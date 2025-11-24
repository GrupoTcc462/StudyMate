from django import forms
from .models import Mensagem


class MensagemForm(forms.ModelForm):
    """
    Formulário para envio de mensagens
    """
    
    class Meta:
        model = Mensagem
        fields = ['mensagem', 'anexo']
        widgets = {
            'mensagem': forms.Textarea(attrs={
                'class': 'form-control message-input',
                'rows': 3,
                'placeholder': 'Digite sua mensagem...',
                'maxlength': '1000'
            }),
            'anexo': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': '.pdf,.doc,.docx,.jpg,.jpeg,.png,.zip'
            }),
        }
        labels = {
            'mensagem': 'Mensagem',
            'anexo': 'Anexo (opcional)',
        }
    
    def clean_mensagem(self):
        mensagem = self.cleaned_data.get('mensagem', '').strip()
        
        if not mensagem:
            raise forms.ValidationError('A mensagem não pode estar vazia.')
        
        if len(mensagem) > 1000:
            raise forms.ValidationError('A mensagem não pode ter mais de 1000 caracteres.')
        
        return mensagem
    
    def clean_anexo(self):
        anexo = self.cleaned_data.get('anexo')
        
        if anexo:
            # Validar tamanho
            if anexo.size > 10 * 1024 * 1024:
                raise forms.ValidationError('O arquivo não pode ser maior que 10MB.')
        
        return anexo