// javascript for word-edit interactions

var wedit_setup = function(hlskey, sourceurl){
    
    // main js function which handles the word-edit page interactions
    // hlskey = "high level source" key for DOM elements
    // sourceurl = module location url

    var trig = $('#hls-trig-' + hlskey);
    var modal = $('#hls-modal-' + hlskey);

    var debuglvl = 0;   // make 1 or 2 for debugging

    // handle trigger for showing modal window
    trig.leanModal({ top:40, overlay:0.8, closeButton: ".close-button"});
    trig.click(function(){
        modal.attr('style', function(i,s) { return s + ' margin-left:0px !important; left:5%' });
        $('#lean_overlay').hide();      // hide gray overlay

        // setup file input
        // need to insert this only after hls triggered, because otherwise it
        // causes other <form> elements to become multipart/form-data, 
        // thus breaking multiple-choice input forms, for example.
        modal.find('#hls-finput').append('<input type="file" name="wordfile" id="wordfile" />');
        on_wordfile_change();   // setup change function
    });

    // functions for logging (debugging)
    var mylog_dbug = function(msg, lvl){
        if (debuglvl>lvl){
            mylog(msg);
        }
    };

    var mylog = function(msg){
        if (debuglvl>0){
            console.log(msg);
        }
    };

    // drag-and-drop (on modal) for file upload
    modal.find('#dropzone')
        .on("dragenter", onDragEnter)
        .on("dragover", onDragOver)
        .on("dragleave", onDragLeave)
        .on("drop", onDrop);

    var onDragEnter = function(event) {
        event.preventDefault();
        $(this).addClass("dragover");
    }, 
    
    onDragOver = function(event) {
        event.preventDefault(); 
        if(!$(this).hasClass("dragover"))
            $(this).addClass("dragover");
    }, 
    
    onDragLeave = function(event) {
        event.preventDefault();
        $(this).removeClass("dragover");
    },
    
    onDrop = function(event) {
        mylog('onDrop');
        event.preventDefault();
        $(this).removeClass("dragover");
        var file = event.originalEvent.dataTransfer.files[0];
        mylog_dbug("file=", 1);
        mylog_dbug(file, 1);
        el = $(this).closest('.upload-modal');
        process_file(sourceurl, file);
        mylog_dbug('onDrop done', 1);
    }
    
    // convert automatically immediately after file is chosen
    on_wordfile_change = function(){
        modal.find('#wordfile').change(function() {
            var file = this.files[0];
            mylog('handler for wordfile input called, file = '+ file);
            process_file(sourceurl, file);
        });
    }
    
    set_status = function(msg, spinon){
        if (spinon){
            msg = msg + '<span class="spinner-in-field-icon"></span>';
        }
        modal.find("#progress")[0].innerHTML = msg;
    }
    
    process_file = function(location, file){
        var el = modal;
        set_status("Processing file " + file.name + "...", true);
        mylog('wordfile:');
        mylog(file);
    
        $.ajax({
            url: "https://studio-input-filter.mitx.mit.edu/word2edx?raw=1",
            type: "POST",
            data: file,
            crossDomain: true,
            processData: false,
            success: function(data){
                mylog('word2edx success!');
                mylog(data);
                xml = data.xml;
                if (xml.length==0){
                    alert('Conversion failed!  error:'+ data.message);
                    set_status("Conversion failed - please try another file", false);
                    $('#wordfileReset').click()
                }else{
                    set_status("Done!  uploading images...", true);
                    post_images(location, data, file);
                    // post_source_code(el, location, file);
                }
            },
            error: function() {
                alert('Error: cannot connect to word2edx server');
                mylog('error!');
            }
        });
    }
    
    post_images = function(location, data, file){
        el = modal;
        $.ajax({
            url: "/put_source_images/" + location,
            type: "POST",
            data: JSON.stringify(data),
            processData: false,
            success: function(immap){
                mylog('images uploaded successfully');
                mylog(immap);
                for (idx in immap){
                    imurlmap = immap[idx];
                    mylog_dbug('imurlmap = ', 2);
                    mylog_dbug(imurlmap, 2);
                    // map /static/html/foo-fig001.png to /c4x/mitx/0.1/asset/problem-X14AZ-fig001.png etc.
                    data.xml = data.xml.replace(RegExp(imurlmap['imurl'],'g'),imurlmap['conurl']);
                }
                mylog_dbug('new xml = ' + data.xml, 3);
                word_set_raw_edit_box(data.xml);
                set_status("Done!  uploading xml...", true);
                post_source_code(location, file);
            },
            error: function() {
                alert('Error: image upload failed!');
                set_status("Image upload failed!  Please try again, or try another file.", false);
                mylog('error!');
            }
        });
    }
    
    word_set_raw_edit_box = function(xml){
        // get the codemirror editor for the raw-edit-box
        // it's a CodeMirror-wrap class element
        modal.closest('.component').find('.CodeMirror-wrap')[0].CodeMirror.setValue(xml);
    }

    post_source_code = function(location, file){
        el = modal;
        // from https://developer.mozilla.org/en-US/docs/Using_files_from_web_applications
        var uri = "/put_source/" + location;
        var xhr = new XMLHttpRequest();
        var fd = new FormData();
        
        xhr.open("POST", uri, true);
        xhr.onreadystatechange = function() {
            if (xhr.readyState == 4 && xhr.status == 200) {
                // Handle response.
                mylog('source_code uploaded successfully');  // or alert(xhr.responseText); // handle response.
                set_status("Done!  closing...", false);
                save_and_close();
            }
        };
        fd.append('source_code', file);
        // Initiate a multipart/form-data upload
        xhr.setRequestHeader("X-CSRFToken", "${csrf_token}");
        xhr.send(fd);
    }

    // save button
    function save_and_close(){
        modal.closest('.component').find('.save-button').click();
    }
    
    // add upload and download links / buttons to component edit box
    modal.closest('.component').find('.component-actions').append('<div id="link-'+hlskey+'" style="float:right;"></div>');
    $('#link-'+hlskey).html('<a class="upload-button standard" id="upload-'+hlskey+'">upload</a>');
    $('#upload-'+hlskey).click(function(){
        modal.closest('.component').find('.edit-button').trigger('click'); // open up editor window
        trig.trigger('click');  // open up HLS editor window
        modal.find('#wordfile').trigger('click');
    });

}

