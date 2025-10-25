"""Funções auxiliares para o módulo Notes"""

def user_is_professor(user):
    """
    Verifica se o usuário é professor
    Retorna True se for professor ou staff/admin
    """
    if not user or not user.is_authenticated:
        return False
    
    # Verifica pelo campo user_type (modelo customizado)
    if hasattr(user, 'user_type'):
        return user.user_type == 'professor' or user.is_staff
    
    # Fallback: verifica grupo Professor
    return user.is_staff or user.groups.filter(name='Professor').exists()


def get_professor_subject(user):
    """
    Retorna a matéria do professor se ele tiver uma
    Pode ser expandido para usar UserProfile.subject se implementado
    """
    if not user_is_professor(user):
        return None
    
    # Se houver UserProfile com subject, usar aqui
    # if hasattr(user, 'userprofile') and user.userprofile.subject:
    #     return user.userprofile.subject
    
    return None