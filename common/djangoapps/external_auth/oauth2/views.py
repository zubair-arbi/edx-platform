from django.shortcuts import render_to_response
from django.http import HttpResponseRedirect
from django.template import RequestContext
from django.contrib.auth.decorators import login_required
from oauth2app.authorize import Authorizer, MissingRedirectURI, AuthorizationException
from .forms import AuthorizeForm

from uni_form.helpers import FormHelper, Submit


@login_required
def missing_redirect_uri(request):
    return render_to_response('oauth2/missing_redirect_uri.html',
                              {},
                              RequestContext(request))


@login_required
def authorize(request):
    authorizer = Authorizer()
    try:
        authorizer.validate(request)
    except MissingRedirectURI, e:
        return HttpResponseRedirect("/oauth2/missing_redirect_uri")
    except AuthorizationException, e:
        # The request is malformed or invalid. Automatically
        # redirects to the provided redirect URL.
        return authorizer.error_redirect()
    if request.method == 'GET':
        template = {
                    "client": authorizer.client,
                    "access_ranges": authorizer.access_ranges
        }
#        # Use any form, make sure it has CSRF protections.
#        template["form"] = AuthorizeForm()
#        # Appends the original OAuth2 parameters.
#        template["form_action"] = '/oauth2/authorize?%s' % authorizer.query_string
        template["form"] = AuthorizeForm()
        helper = FormHelper()
        no_submit = Submit('connect', 'No')
        helper.add_input(no_submit)
        yes_submit = Submit('connect', 'Yes')
        helper.add_input(yes_submit)
        helper.form_action = '/oauth2/authorize?%s' % authorizer.query_string
        helper.form_method = 'POST'
        template["helper"] = helper
        return render_to_response(
            'oauth2/authorize.html',
            template,
            RequestContext(request))
    elif request.method == 'POST':
        form = AuthorizeForm(request.POST)
        if form.is_valid():
            if request.POST.get("connect") == "Yes":
                # User agrees. Redirect to redirect_uri with success params.
                return authorizer.grant_redirect()
            else:
                # User refuses. Redirect to redirect_uri with error params.
                return authorizer.error_redirect()
    return HttpResponseRedirect("/")
