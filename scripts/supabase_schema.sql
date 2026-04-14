-- ============================================
-- EXECUTE ESTE SQL NO SUPABASE SQL EDITOR
-- Acesse: supabase.com → seu projeto → SQL Editor
-- ============================================

-- Tabela principal de denúncias
CREATE TABLE IF NOT EXISTS complaints (
    id TEXT PRIMARY KEY,
    nome TEXT NOT NULL,
    contato TEXT NOT NULL,
    descricao TEXT NOT NULL,
    localidade TEXT,
    data_ocorrido TEXT,
    orgao_relacionado TEXT,
    categoria_sugerida TEXT DEFAULT 'OUTROS',
    subcategoria TEXT,
    gravidade TEXT DEFAULT 'MEDIA',
    tem_evidencia BOOLEAN DEFAULT FALSE,
    status TEXT DEFAULT 'PENDENTE',
    classificacao_ia JSONB,
    confianca_ia FLOAT DEFAULT 0.0,
    criado_em TIMESTAMPTZ DEFAULT NOW()
);

-- Índices para o painel público
CREATE INDEX IF NOT EXISTS idx_complaints_status ON complaints(status);
CREATE INDEX IF NOT EXISTS idx_complaints_categoria ON complaints(categoria_sugerida);
CREATE INDEX IF NOT EXISTS idx_complaints_criado ON complaints(criado_em DESC);

-- Tabela de log de interações (para análise)
CREATE TABLE IF NOT EXISTS interactions (
    id BIGSERIAL PRIMARY KEY,
    phone TEXT NOT NULL,
    agent TEXT NOT NULL,
    user_message TEXT,
    bot_response TEXT,
    criado_em TIMESTAMPTZ DEFAULT NOW()
);

-- View para painel público (sem dados pessoais)
CREATE OR REPLACE VIEW public_complaints AS
SELECT
    id,
    categoria_sugerida,
    subcategoria,
    gravidade,
    localidade,
    orgao_relacionado,
    status,
    tem_evidencia,
    criado_em,
    -- Remove dados pessoais
    LEFT(descricao, 200) AS descricao_resumida
FROM complaints
WHERE status != 'CANCELADO';

-- RLS: linha por linha de segurança
ALTER TABLE complaints ENABLE ROW LEVEL SECURITY;
ALTER TABLE interactions ENABLE ROW LEVEL SECURITY;

-- Permite insert via service key (backend)
CREATE POLICY "service_insert_complaints"
ON complaints FOR INSERT
TO service_role
WITH CHECK (true);

CREATE POLICY "service_select_complaints"
ON complaints FOR SELECT
TO service_role
USING (true);

-- Painel público: leitura da view sem autenticação
GRANT SELECT ON public_complaints TO anon;
