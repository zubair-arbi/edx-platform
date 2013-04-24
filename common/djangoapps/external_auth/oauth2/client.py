from django.shortcuts import render_to_response
from django.template import RequestContext
from oauth2app.models import Client, AccessToken, Code
from base64 import b64encode

from django.contrib.auth.decorators import login_required
from external_auth.oauth2.forms import CreateClientForm, ClientRemoveForm


def client(request, client_id):
    client = Client.objects.get(key=client_id)
    template = {
        "client": client,
        "basic_auth": "Basic %s" % b64encode(client.key + ":" + client.secret),
        "codes": Code.objects.filter(client=client).select_related(),
        "access_tokens": AccessToken.objects.filter(client=client).select_related()}
    template["error_description"] = request.GET.get("error_description")
    return render_to_response(
        'oauth2/client.html',
        template,
        RequestContext(request))


@login_required
def clients(request):
    if request.method == "POST":
        form = CreateClientForm(request.POST)
        remove_form = ClientRemoveForm(request.POST)
        if form.is_valid():
            Client.objects.create(
                name=form.cleaned_data["name"],
                user=request.user)
        elif remove_form.is_valid():
            Client.objects.filter(
                id=remove_form.cleaned_data["client_id"]).delete()
            form = CreateClientForm()
    else:
        form = CreateClientForm()
    template = {
        "form": form,
        "clients": Client.objects.filter(user=request.user)}
    return render_to_response(
        'oauth2/clients.html',
        template,
        RequestContext(request))


def status(request):
    template = {}
    if request.user.is_authenticated():
        clients = Client.objects.filter(user=request.user)
        access_tokens = AccessToken.objects.filter(user=request.user)
        access_tokens = access_tokens.select_related()
        template["access_tokens"] = access_tokens
        template["clients"] = clients
    return render_to_response(
        'oauth2/homepage.html',
        template,
        RequestContext(request))
