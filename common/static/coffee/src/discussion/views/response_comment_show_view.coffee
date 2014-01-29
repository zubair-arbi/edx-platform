if Backbone?
  class @ResponseCommentShowView extends DiscussionContentView

    tagName: "li"

    initialize: ->
        super()
        @model.on "change", @updateModelDetails

    render: ->
      @template = _.template($("#response-comment-show-template").html())
      params = @model.toJSON()

      @$el.html(@template(params))
      @initLocal()
      @delegateEvents()
      @renderAttrs()
      @renderFlagged()
      @markAsStaff()
      @$el.find(".timeago").timeago()
      @convertMath()
      @addReplyLink()
      @

    addReplyLink: () ->
      if @model.hasOwnProperty('parent')
        name = @model.parent.get('username') ? gettext("anonymous")
        html = "<a href='#comment_#{@model.parent.id}'>@#{name}</a>:  "
        p = @$('.response-body p:first')
        p.prepend(html)

    convertMath: ->
      body = @$el.find(".response-body")
      body.html DiscussionUtil.postMathJaxProcessor DiscussionUtil.markdownWithHighlight body.text()
      MathJax.Hub.Queue ["Typeset", MathJax.Hub, body[0]]

    markAsStaff: ->
      if DiscussionUtil.isStaff(@model.get("user_id"))
        @$el.find("a.profile-link").after('<span class="staff-label">' + gettext('staff') + '</span>')
      else if DiscussionUtil.isTA(@model.get("user_id"))
        @$el.find("a.profile-link").after('<span class="community-ta-label">' + gettext('Community TA') + '</span>')


    renderFlagged: =>
      if window.user.id in @model.get("abuse_flaggers") or (DiscussionUtil.isFlagModerator and @model.get("abuse_flaggers").length > 0)
        @$("[data-role=thread-flag]").addClass("flagged")
        @$("[data-role=thread-flag]").removeClass("notflagged")
        @$(".discussion-flag-abuse").attr("aria-pressed", "true")
        @$(".discussion-flag-abuse").attr("data-tooltip", gettext("Misuse Reported, click to remove report"))
        @$(".discussion-flag-abuse .flag-label").html(gettext("Misuse Reported, click to remove report"))
      else
        @$("[data-role=thread-flag]").removeClass("flagged")
        @$("[data-role=thread-flag]").addClass("notflagged")
        @$(".discussion-flag-abuse").attr("aria-pressed", "false")
        @$(".discussion-flag-abuse").attr("data-tooltip", gettext("Report Misuse"))
        @$(".discussion-flag-abuse .flag-label").html(gettext("Report Misuse"))

    updateModelDetails: =>
      @renderFlagged()


