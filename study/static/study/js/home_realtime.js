// ========================================
// STUDYMATE - ATUALIZAÇÃO EM TEMPO REAL
// Sistema de atualização automática dos cards da home
// ========================================

(function() {
    'use strict';
    
    // Configurações
    const CONFIG = {
        UPDATE_INTERVAL: 3000, // Atualizar a cada 3 segundos
        API_BASE: '/study/api/',
        ENDPOINTS: {
            stats: 'stats/',
            materias: 'materias_count/',
            notes: 'notes_count/',
            online: 'online_students/'
        }
    };
    
    // Estado global
    let updateTimer = null;
    let isUpdating = false;
    
    // ========================================
    // FUNÇÃO PRINCIPAL: BUSCAR TODAS AS ESTATÍSTICAS
    // ========================================
    async function fetchAllStats() {
        if (isUpdating) return;
        
        isUpdating = true;
        
        try {
            const response = await fetch(CONFIG.API_BASE + CONFIG.ENDPOINTS.stats, {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }
            
            const data = await response.json();
            
            if (data.success) {
                updateAllCards(data);
                console.log('✅ Stats atualizados:', {
                    materias: data.materias_count,
                    notes: data.notes_count,
                    alunos: data.alunos_online_count
                });
            } else {
                console.error('❌ Erro na resposta:', data.error);
            }
            
        } catch (error) {
            console.error('❌ Erro ao buscar estatísticas:', error);
        } finally {
            isUpdating = false;
        }
    }
    
    // ========================================
    // ATUALIZAR CARDS COM ANIMAÇÃO
    // ========================================
    function updateAllCards(data) {
        // Card 1: Matérias
        updateCard('materias', data.materias_count, 
            data.materias_count === 0 ? 'Nenhuma matéria cadastrada' : 
            data.materias_count === 1 ? 'Matéria disponível' : 'Matérias disponíveis');
        
        // Card 2: Alunos Online
        updateCard('alunos', data.alunos_online_count,
            data.alunos_online_count === 0 ? 'Nenhum aluno online' :
            data.alunos_online_count === 1 ? 'Estudante online' : 'Estudantes online');
        
        // Salvar lista de alunos online no estado global
        window.statsData = window.statsData || {};
        window.statsData.alunos_online = data.alunos_online || [];
        
        // Card 3: Notes
        updateCard('notes', data.notes_count,
            data.notes_count === 0 ? 'Nenhum note criado' :
            data.notes_count === 1 ? 'Note compartilhado' : 'Notes compartilhados');
    }
    
    // ========================================
    // ATUALIZAR CARD INDIVIDUAL COM ANIMAÇÃO
    // ========================================
    function updateCard(tipo, newValue, newLabel) {
        const countElement = document.getElementById(`${tipo}-count`);
        const labelElement = document.getElementById(`${tipo}-label`);
        
        if (!countElement || !labelElement) return;
        
        const oldValue = parseInt(countElement.textContent) || 0;
        
        // Animação apenas se o valor mudou
        if (oldValue !== newValue) {
            // Adicionar efeito de pulso
            countElement.style.transform = 'scale(1.2)';
            countElement.style.transition = 'transform 0.3s ease';
            
            setTimeout(() => {
                countElement.textContent = newValue;
                countElement.style.transform = 'scale(1)';
            }, 150);
        }
        
        // Atualizar label
        labelElement.textContent = newLabel;
    }
    
    // ========================================
    // POPUP: ALUNOS ONLINE (ATUALIZADO)
    // ========================================
    window.abrirAlunosOnline = async function() {
        const content = document.getElementById('alunos-online-content');
        
        if (!content) {
            console.error('❌ Elemento alunos-online-content não encontrado');
            return;
        }
        
        // Mostrar loading
        content.innerHTML = `
            <div style="text-align: center; padding: 40px;">
                <div style="font-size: 3rem; margin-bottom: 15px;">⏳</div>
                <p style="color: #6c757d;">Carregando alunos online...</p>
            </div>
        `;
        
        // Abrir popup
        const popup = document.getElementById('popup-alunos-online');
        if (popup) {
            popup.classList.add('active');
        }
        
        try {
            // Buscar dados atualizados
            const response = await fetch(CONFIG.API_BASE + CONFIG.ENDPOINTS.online, {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }
            
            const data = await response.json();
            
            if (data.success) {
                if (data.count === 0) {
                    content.innerHTML = `
                        <div class="empty-message">
                            <span class="emoji">😴</span>
                            <h4>Nenhum aluno online no momento</h4>
                            <p>Parece que todos estão descansando ou estudando offline!</p>
                        </div>
                    `;
                } else {
                    let html = '';
                    data.students.forEach(aluno => {
                        html += `
                            <div class="aluno-item">
                                <div class="aluno-nome">${aluno.username}</div>
                                <div class="aluno-status">🟢 Online - ${aluno.tempo_texto}</div>
                            </div>
                        `;
                    });
                    content.innerHTML = html;
                }
            } else {
                throw new Error(data.error || 'Erro desconhecido');
            }
            
        } catch (error) {
            console.error('❌ Erro ao carregar alunos online:', error);
            content.innerHTML = `
                <div class="empty-message">
                    <span class="emoji">⚠️</span>
                    <h4>Erro ao carregar dados</h4>
                    <p>Não foi possível conectar ao servidor. Tente novamente.</p>
                </div>
            `;
        }
    };
    
    // ========================================
    // POPUP: MATÉRIAS
    // ========================================
    window.abrirMaterias = async function() {
        try {
            const response = await fetch(CONFIG.API_BASE + CONFIG.ENDPOINTS.materias);
            const data = await response.json();
            
            if (data.success && data.count === 0) {
                mostrarAlerta(
                    '📚',
                    'Nenhuma matéria cadastrada ainda',
                    'Em breve novas matérias serão adicionadas pela equipe!'
                );
            } else {
                window.location.href = '/materias/';
            }
        } catch (error) {
            console.error('❌ Erro ao verificar matérias:', error);
            window.location.href = '/materias/';
        }
    };
    
    // ========================================
    // POPUP: NOTES
    // ========================================
    window.abrirNotes = async function() {
        try {
            const response = await fetch(CONFIG.API_BASE + CONFIG.ENDPOINTS.notes);
            const data = await response.json();
            
            if (data.success && data.count === 0) {
                mostrarAlerta(
                    '📝',
                    'Nenhum note compartilhado ainda',
                    'Seja o primeiro a criar e compartilhar um note com a comunidade!'
                );
            } else {
                window.location.href = '/notes/';
            }
        } catch (error) {
            console.error('❌ Erro ao verificar notes:', error);
            window.location.href = '/notes/';
        }
    };
    
    // ========================================
    // POPUP: SUPORTE (SEM MUDANÇAS)
    // ========================================
    window.abrirSuporte = function() {
        const popup = document.getElementById('popup-suporte');
        if (popup) {
            popup.classList.add('active');
        }
    };
    
    // ========================================
    // FECHAR POPUP
    // ========================================
    window.fecharPopup = function(tipo) {
        const popup = document.getElementById(`popup-${tipo}`);
        if (popup) {
            popup.classList.remove('active');
        }
    };
    
    // ========================================
    // ALERTA CUSTOMIZADO
    // ========================================
    window.mostrarAlerta = function(icone, titulo, mensagem) {
        const overlay = document.getElementById('alert-overlay');
        
        const alertDiv = document.createElement('div');
        alertDiv.className = 'custom-alert';
        alertDiv.innerHTML = `
            <div class="alert-icon">${icone}</div>
            <h4>${titulo}</h4>
            <p>${mensagem}</p>
            <button onclick="fecharAlerta()">Entendi</button>
        `;
        
        overlay.classList.add('show');
        document.body.appendChild(alertDiv);
        
        overlay.onclick = window.fecharAlerta;
    };
    
    window.fecharAlerta = function() {
        const overlay = document.getElementById('alert-overlay');
        const alert = document.querySelector('.custom-alert');
        
        if (alert) {
            alert.style.animation = 'alertPop 0.3s ease reverse';
            setTimeout(() => {
                alert.remove();
                overlay.classList.remove('show');
            }, 300);
        }
    };
    
    // ========================================
    // INICIALIZAÇÃO
    // ========================================
    function init() {
        console.log('🚀 Sistema de atualização em tempo real iniciado');
        
        // Buscar dados inicial
        fetchAllStats();
        
        // Configurar atualização automática
        updateTimer = setInterval(fetchAllStats, CONFIG.UPDATE_INTERVAL);
        
        // Event listeners para popups
        setupPopupListeners();
        
        console.log(`✅ Atualização automática configurada (${CONFIG.UPDATE_INTERVAL / 1000}s)`);
    }
    
    // ========================================
    // CONFIGURAR LISTENERS DE POPUP
    // ========================================
    function setupPopupListeners() {
        // Fechar ao clicar fora
        document.querySelectorAll('.popup-overlay').forEach(overlay => {
            overlay.addEventListener('click', function(e) {
                if (e.target === this) {
                    this.classList.remove('active');
                }
            });
        });
        
        // Fechar com ESC
        document.addEventListener('keydown', function(e) {
            if (e.key === 'Escape') {
                document.querySelectorAll('.popup-overlay.active').forEach(overlay => {
                    overlay.classList.remove('active');
                });
                
                // Fechar alertas também
                const overlay = document.getElementById('alert-overlay');
                if (overlay && overlay.classList.contains('show')) {
                    window.fecharAlerta();
                }
            }
        });
    }
    
    // ========================================
    // LIMPAR AO SAIR DA PÁGINA
    // ========================================
    window.addEventListener('beforeunload', function() {
        if (updateTimer) {
            clearInterval(updateTimer);
        }
    });
    
    // Iniciar quando o DOM estiver pronto
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
    
})();