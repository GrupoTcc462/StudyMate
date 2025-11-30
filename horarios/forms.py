from django import forms
from .models import Horario


class HorarioImportForm(forms.ModelForm):
    """
    Formulário para importação de horários
    """
    
    class Meta:
        model = Horario
        fields = ['arquivo']
        widgets = {
            'arquivo': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': '.jpg,.jpeg,.png,.xlsx,.xls',
                'id': 'arquivoInput'
            })
        }
        labels = {
            'arquivo': 'Selecione o arquivo'
        }
    
    def clean_arquivo(self):
        arquivo = self.cleaned_data.get('arquivo')
        
        if not arquivo:
            raise forms.ValidationError('Nenhum arquivo foi selecionado.')
        
        # Validar tamanho
        if arquivo.size > 5 * 1024 * 1024:
            raise forms.ValidationError('O arquivo não pode ser maior que 5MB.')
        
        # Validar extensão
        import os
        ext = os.path.splitext(arquivo.name)[1].lower()
        allowed = ['.jpg', '.jpeg', '.png', '.xlsx', '.xls']
        
        if ext not in allowed:
            raise forms.ValidationError(
                f'Formato não suportado. Use: {", ".join(allowed)}'
            )
        
        return arquivo