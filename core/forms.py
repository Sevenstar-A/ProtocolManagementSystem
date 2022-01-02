from django import forms
ACCEPTABLE_DOCUMENT_TYPES_STR = '.doc, .docx, .pdf, .xlsx'
ACCEPTABLE_IMAGE_TYPES_STR = '.png, .jpg, .jiff, .gif'


class FileSubmitForm(forms.Form): # used to validate file inputs
    """ required default = True, field_name default = 'file_doc'
    """
    def __init__(self,*args, **kwargs):
        field_name = kwargs.pop('field_name','file_doc')
        required = kwargs.pop('required', True)
        super(FileSubmitForm, self).__init__(*args, **kwargs)
        if field_name:
            self.fields[field_name] = forms.FileField(required=required, widget = forms.FileInput(attrs={'class':'custom-file-input', 'accept':ACCEPTABLE_DOCUMENT_TYPES_STR}))
    
    
class MultipleFileSubmit(forms.Form):
    def __init__(self,*args, **kwargs):
        field_name = kwargs.pop('field_name', 'file_docs')
        required = kwargs.pop('required', False)
        super(MultipleFileSubmit, self).__init__(*args, **kwargs)
        if field_name:
            self.fields[field_name] = forms.FileField(required=required, widget = forms.FileInput(attrs={ 'multiple':'true', 'accept':ACCEPTABLE_DOCUMENT_TYPES_STR, 'class':'btn btn-primary' }))
    

class TextSubmitForm(forms.Form): # used to validate Text fields like rejection comment, Special Note
    def __init__(self,*args, **kwargs):
        field_name = kwargs.pop('field_name', "comment_area")
        value = kwargs.pop('value', "")
        required = kwargs.pop('required', False)
        super(TextSubmitForm, self).__init__(*args, **kwargs)
        self.fields[field_name] = forms.CharField(required=required, 
                                    widget=forms.Textarea(attrs={'class':'form-control', 'name':'changed',}))
    
        self.fields[field_name].initial = value