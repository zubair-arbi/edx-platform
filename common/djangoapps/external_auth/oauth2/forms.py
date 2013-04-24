from django import forms
from uni_form.helpers import FormHelper, Submit, Reset


class AuthorizeForm(forms.Form):
    pass


class CreateClientForm(forms.Form):

    name = forms.CharField(label="Name", max_length=30)

    @property
    def helper(self):
        form = CreateClientForm()
        helper = FormHelper()
        reset = Reset('', 'Reset')
        helper.add_input(reset)
        submit = Submit('', 'Create Client')
        helper.add_input(submit)
        helper.form_action = '/oauth2/clients'
        helper.form_method = 'POST'
        return helper


class ClientRemoveForm(forms.Form):

    client_id = forms.IntegerField()
