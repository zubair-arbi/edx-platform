"""
Utility functions for transcripts
"""
import json
import HTMLParser
import StringIO
import requests
import logging
from pysrt import SubRipTime, SubRipItem, SubRipFile
from functools import wraps
from lxml import etree

from cache_toolbox.core import del_cached_content
from django_comment_client.utils import JsonResponse
from django.conf import settings

from xmodule.exceptions import NotFoundError
from xmodule.modulestore.inheritance import own_metadata
from xmodule.contentstore.content import StaticContent
from xmodule.contentstore.django import contentstore
from xmodule.modulestore import Location

log = logging.getLogger(__name__)

# Current youtube api for requesting transcripts
# for example: http://video.google.com/timedtext?lang=en&v=j_jEn79vS3g
YOUTUBE_API = {
    'url': "http://video.google.com/timedtext",
    'params': {'lang': 'en', 'v': 'set_youtube_id_of_11_symbols_here'}
}

# for testing Youtube in acceptance tests
if getattr(settings, 'VIDEO_PORT', None):
    YOUTUBE_API['url'] = "http://127.0.0.1:" + str(settings.VIDEO_PORT) + '/test_transcripts_youtube/'


def return_ajax_status(view_function):
    """Suppose view_function returns True/False, then convert
    response to JSON HTTP response:
        {"success": true} or {"success": false}
    """
    @wraps(view_function)
    def new_view_function(request, *args, **kwargs):
        """New view functions for decorator result."""
        result = view_function(request, *args, **kwargs)
        if isinstance(result, tuple):
            status = result[0]
            response_data = result[1]
        else:
            status = result
            response_data = {}
        response_data.update({'success': status})
        return JsonResponse(response_data)
    return new_view_function


def generate_subs(speed, source_speed, source_subs):
    """Generate and return transcripts dictionary for speed equal to
    `speed` value, using `source_speed` and `source_subs`."""
    if speed == source_speed:
        return source_subs

    coefficient = speed / source_speed
    subs = {
        'start': [
            int(round(timestamp * coefficient)) for
            timestamp in source_subs['start']
        ],
        'end': [
            int(round(timestamp * coefficient)) for
            timestamp in source_subs['end']
        ],
        'text': source_subs['text']}
    return subs


def save_subs_to_store(subs, subs_id, item):
    """Save transcripts into `StaticContent`."""
    filedata = json.dumps(subs, indent=2)
    mime_type = 'application/json'
    filename = 'subs_{0}.srt.sjson'.format(subs_id)

    content_location = StaticContent.compute_location(
        item.location.org, item.location.course, filename)
    content = StaticContent(content_location, filename, mime_type, filedata)
    contentstore().save(content)
    del_cached_content(content_location)
    return content_location


def get_transcripts_from_youtube(youtube_id):
    """
    Gets transcripts from youtube for youtube_id.
    Returns (status, transcripts): bool, dict.
    """
    html_parser = HTMLParser.HTMLParser()
    YOUTUBE_API['params']['v'] = youtube_id
    data = requests.get(
        YOUTUBE_API['url'],
        params=YOUTUBE_API['params']
    )
    if data.status_code != 200 or not data.text:
        log.debug("Can't recieved correct transcripts from Youtube.")
        return False,  {}

    sub_starts, sub_ends, sub_texts = [], [], []

    xmltree = etree.fromstring(str(data.text))
    for element in xmltree:
        if element.tag == "text":
            start = float(element.get("start"))
            duration = float(element.get("dur"))
            text = element.text
            end = start + duration

            if text:
                # Start and end are an int representing the millisecond timestamp.
                sub_starts.append(int(start * 1000))
                sub_ends.append(int((end + 0.0001) * 1000))
                sub_texts.append(html_parser.unescape(text.replace('\n', ' ')))

    return True, {'start': sub_starts, 'end': sub_ends, 'text': sub_texts}


def download_youtube_subs(youtube_subs, item):
    """Download transcripts from Youtube using `youtube_ids`, and
    save them to assets for `item` module.

    Test: http://video.google.com/timedtext?lang=en&v=j_jEn79vS3g
    """
    status_dict = {}

    # Iterate from lowest to highest speed and try to do download transcripts
    # from the Youtube service.
    for speed, youtube_id in sorted(youtube_subs.iteritems()):
        if not youtube_id:
            continue

        status, subs = get_transcripts_from_youtube(youtube_id)
        if not status:
            status_dict.update({speed: status})
            continue

        available_speed = speed
        save_subs_to_store(subs, youtube_id, item)

        log.info(
            """transcripts for Youtube ID {0} (speed {1})
            are downloaded from Youtube and
            saved.""".format(youtube_id, speed)
        )

        status_dict.update({speed: True})

    if not any(status_dict.itervalues()):
        log.error("Can't find any transcripts on the Youtube service.")
        return False

    # When we exit from the previous loop, `available_speed` and `subs`
    # are the transcripts data with the highest speed available on the
    # Youtube service. We use the highest speed as main speed for the
    # generation other transcripts, cause during calculation timestamps
    # for lower speeds we just use multiplication istead of division.

    # Generate transcripts for missed speeds.
    for speed, status in status_dict.iteritems():
        if not status:
            save_subs_to_store(
                generate_subs(speed, available_speed, subs),
                youtube_subs[speed],
                item)

            log.info(
                """transcripts for Youtube ID {0} (speed {1})
                are generated from Youtube ID {2} (speed {3}) and
                saved.""".format(
                youtube_subs[speed],
                speed,
                youtube_subs[available_speed],
                available_speed)
            )

    return True


def remove_subs_from_store(subs_id, item):
    """Remove from store, if transcripts content exists."""
    filename = 'subs_{0}.srt.sjson'.format(subs_id)
    content_location = StaticContent.compute_location(
        item.location.org, item.location.course, filename)
    try:
        content = contentstore().find(content_location)
        contentstore().delete(content.get_id())
    except NotFoundError:
        pass


def manage_video_transcripts(old_item, new_item):
    """Function for managing transcripts."""

    youtube_subs = {
        0.75: new_item.youtube_id_0_75,
        1: new_item.youtube_id_1_0,
        1.25: new_item.youtube_id_1_25,
        1.5: new_item.youtube_id_1_5
    }

    # If user has changed YT id, we remove transcripts.
    if new_item.youtube_id_1_0 != old_item.youtube_id_1_0:
        for youtube_id in youtube_subs.values():
            if youtube_id:
                remove_subs_from_store(youtube_id, new_item)

    # If user has changed HTML5 sources, we remove transcripts.
    old_src = set([src for src in old_item.html5_sources if src])
    new_src = set([src for src in new_item.html5_sources if src])
    if (old_src - new_src) and old_item.sub:
        remove_subs_from_store(old_item.sub, new_item)
        if new_item.sub == old_item.sub:
            new_item.sub = ''
            new_item.save()
            store = get_modulestore(Location(new_item.location))
            store.update_metadata(new_item.location, own_metadata(new_item))

    # Always download fresh transcripts from Youtube service if video
    # module has youtube type.
    if new_item.youtube_id_1_0:
        download_youtube_subs(youtube_subs, new_item)


def generate_subs_from_source(speed_subs, subs_type, subs_filedata, item):
    """Generate transcripts from source files (like SubRip format, etc.)
    and save them to assets for `item` module.
    We expect, that speed of source subs equal to 1

    :param speed_subs: dictionary {speed: sub_id, ...}
    :param subs_type: type of source subs: "srt", ...
    :param subs_filedata: content of source subs.
    :param item: module object.
    :returns: True, if all subs are generated and saved successfully.
    """
    html_parser = HTMLParser.HTMLParser()

    if subs_type != 'srt':
        log.error("We support only SubRip (*.srt) transcripts format.")
        return False

    srt_subs_obj = SubRipFile.from_string(subs_filedata)
    if not srt_subs_obj:
        log.error("Something wrong with SubRip transcripts file during parsing.")
        return False

    sub_starts = []
    sub_ends = []
    sub_texts = []

    for sub in srt_subs_obj:
        sub_starts.append(sub.start.ordinal)
        sub_ends.append(sub.end.ordinal)
        sub_texts.append(html_parser.unescape(sub.text.replace('\n', ' ')))

    subs = {
        'start': sub_starts,
        'end': sub_ends,
        'text': sub_texts}

    for speed, subs_id in speed_subs.iteritems():
        save_subs_to_store(
            generate_subs(speed, 1, subs),
            subs_id,
            item)

    return True


def generate_srt_from_sjson(sjson_subs, speed):
    """Generate transcripts with speed = 1.0 from sjson to SubRip (*.srt).

    :param sjson_subs: "sjson" subs.
    :param speed: speed of `sjson_subs`.
    :returns: "srt" subs.
    """
    if len(sjson_subs['start']) != len(sjson_subs['end']) or \
       len(sjson_subs['start']) != len(sjson_subs['text']):
        return None

    sjson_speed_1 = generate_subs(speed, 1, sjson_subs)
    output = StringIO.StringIO()

    for i in range(len(sjson_speed_1['start'])):
        item = SubRipItem(
            index=i,
            start=SubRipTime(milliseconds=sjson_speed_1['start'][i]),
            end=SubRipTime(milliseconds=sjson_speed_1['end'][i]),
            text=sjson_speed_1['text'][i])
        output.write(unicode(item))
        output.write('\n')

    output.seek(0)

    return output.read()