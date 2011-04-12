from django import forms

class EmailInput(forms.TextInput):
    input_type = 'email'

