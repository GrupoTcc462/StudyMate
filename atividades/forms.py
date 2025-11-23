from django import forms
from .models import Atividade, AtividadeEnvio


class AtividadeForm(forms.ModelForm):
    """
    Formulário para criação de atividades por professores
    """
    
    class Meta:
        model = Atividade
        fields = [
            'titulo', 
            'descricao', 
            'tipo', 
            'ano_1', 
            'ano_2', 
            'ano_3', 
            'todos',
            'prazo_entrega', 
            'permite_envio', 
            'anexo'
        ]
        widgets = {
            'titulo': forms.TextInput(attrs={
                'class': 'form-control',
                'maxlength': '50',
                'placeholder': 'Ex: Trabalho de História - Revolução Industrial'
            }),
            'descricao': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'maxlength': '800',
                'placeholder': 'Orientações e instruções da atividade...'
            }),
            'tipo': forms.Select(attrs={'class': 'form-select'}),
            'prazo_entrega': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local'
            }),
            'permite_envio': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'ano_1': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'ano_2': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'ano_3': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'todos': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'anexo': forms.FileInput(attrs={'class': 'form-control'}),
        }
        labels = {
            'titulo': 'Título *',
            'descricao': 'Descrição / Orientações',
            'tipo': 'Tipo de Atividade *',
            'ano_1': '1º Ano',
            'ano_2': '2º Ano',
            'ano_3': '3º Ano',
            'todos': 'Todos os Anos',
            'prazo_entrega': 'Prazo de Entrega',
            'permite_envio': 'Permite envio pelo aluno?',
            'anexo': 'Anexo (opcional)',
        }
    
    def clean(self):
        cleaned_data = super().clean()
        tipo = cleaned_data.get('tipo')
        
        # Desabilitar envio para avisos
        if tipo in ['AVISO_PROVA', 'AVISO_SIMPLES']:
            cleaned_data['permite_envio'] = False
        
        # Validar público-alvo
        ano_1 = cleaned_data.get('ano_1')
        ano_2 = cleaned_data.get('ano_2')
        ano_3 = cleaned_data.get('ano_3')
        todos = cleaned_data.get('todos')
        
        if not any([ano_1, ano_2, ano_3, todos]):
            raise forms.ValidationError('Selecione pelo menos um ano ou "Todos".')
        
        return cleaned_data


class AtividadeEnvioForm(forms.ModelForm):
    """
    Formulário para envio de atividades por alunos
    """
    
    class Meta:
        model = AtividadeEnvio
        fields = ['arquivo']
        widgets = {
            'arquivo': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': '.pdf,.doc,.docx,.jpg,.jpeg,.png,.zip'
            }),
        }
        labels = {
            'arquivo': 'Arquivo da Atividade *',
        }
    
    def clean_arquivo(self):
        arquivo = self.cleaned_data.get('arquivo')
        
        if not arquivo:
            raise forms.ValidationError('Selecione um arquivo para enviar.')
        
        # Validar tamanho
        if arquivo.size > 10 * 1024 * 1024:
            raise forms.ValidationError('O arquivo não pode ser maior que 10MB.')
        
        return arquivo