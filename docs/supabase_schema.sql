-- ================================================================
--  supabase_schema.sql
--  Cole este script inteiro no Supabase SQL Editor e execute.
--  Menu: Database > SQL Editor > New Query > Cole > Run
-- ================================================================

-- ── 1. PRODUTOS ─────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.produtos (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    nome        TEXT NOT NULL,
    descricao   TEXT,
    preco       NUMERIC(10,2) NOT NULL CHECK (preco > 0),
    estoque     INTEGER NOT NULL DEFAULT 0 CHECK (estoque >= 0),
    imagem_url  TEXT,
    categoria   TEXT DEFAULT 'Geral',
    peso_gramas INTEGER DEFAULT 300,
    ativo       BOOLEAN NOT NULL DEFAULT TRUE,
    criado_em   TIMESTAMPTZ DEFAULT NOW()
);

-- ── 2. ENDEREÇOS ────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.enderecos (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id      UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    apelido      TEXT NOT NULL DEFAULT 'Casa',
    cep          TEXT NOT NULL,
    logradouro   TEXT NOT NULL,
    numero       TEXT NOT NULL,
    complemento  TEXT DEFAULT '',
    bairro       TEXT NOT NULL,
    cidade       TEXT NOT NULL,
    uf           CHAR(2) NOT NULL,
    principal    BOOLEAN NOT NULL DEFAULT FALSE,
    criado_em    TIMESTAMPTZ DEFAULT NOW()
);

-- ── 3. PEDIDOS ──────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.pedidos (
    id               UUID PRIMARY KEY,
    user_id          UUID NOT NULL REFERENCES auth.users(id),
    produto_id       UUID REFERENCES public.produtos(id),
    produto_nome     TEXT NOT NULL,
    produto_preco    NUMERIC(10,2) NOT NULL,
    quantidade       INTEGER NOT NULL DEFAULT 1,
    subtotal         NUMERIC(10,2) NOT NULL,
    frete_servico    TEXT DEFAULT 'PAC',
    frete_valor      NUMERIC(10,2) DEFAULT 0,
    frete_prazo      INTEGER DEFAULT 7,
    total            NUMERIC(10,2) NOT NULL,
    forma_pagamento  TEXT NOT NULL DEFAULT 'pix',
    status           TEXT NOT NULL DEFAULT 'PENDENTE',
    endereco_id      UUID REFERENCES public.enderecos(id),
    endereco_cep     TEXT,
    endereco_cidade  TEXT,
    endereco_uf      TEXT,
    criado_em        TIMESTAMPTZ DEFAULT NOW()
);

-- ── 4. EVENTOS DE PEDIDO ────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.eventos_pedido (
    id          BIGSERIAL PRIMARY KEY,
    pedido_id   UUID NOT NULL REFERENCES public.pedidos(id) ON DELETE CASCADE,
    servico     TEXT NOT NULL,
    status      TEXT NOT NULL,
    mensagem    TEXT,
    criado_em   TIMESTAMPTZ DEFAULT NOW()
);

-- ── 5. ROW LEVEL SECURITY (RLS) ─────────────────────────────────
-- Usuários só enxergam seus próprios dados.
-- O backend usa service_role_key e ignora RLS.

ALTER TABLE public.enderecos    ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.pedidos      ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.eventos_pedido ENABLE ROW LEVEL SECURITY;

-- Endereços: usuário vê/edita apenas os seus
CREATE POLICY "usuario_ver_enderecos"
    ON public.enderecos FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "usuario_inserir_enderecos"
    ON public.enderecos FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "usuario_deletar_enderecos"
    ON public.enderecos FOR DELETE
    USING (auth.uid() = user_id);

-- Pedidos: usuário vê apenas os seus
CREATE POLICY "usuario_ver_pedidos"
    ON public.pedidos FOR SELECT
    USING (auth.uid() = user_id);

-- Eventos: usuário vê apenas os dos seus pedidos
CREATE POLICY "usuario_ver_eventos"
    ON public.eventos_pedido FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM public.pedidos p
            WHERE p.id = eventos_pedido.pedido_id
            AND p.user_id = auth.uid()
        )
    );

-- Produtos: leitura pública
ALTER TABLE public.produtos ENABLE ROW LEVEL SECURITY;
CREATE POLICY "produtos_leitura_publica"
    ON public.produtos FOR SELECT
    USING (TRUE);

-- ── 6. PRODUTOS DE EXEMPLO ──────────────────────────────────────
-- Execute após criar as tabelas acima.

INSERT INTO public.produtos (nome, descricao, preco, estoque, categoria, peso_gramas, imagem_url) VALUES
(
    'Notebook Gamer RTX 4060',
    'Processador Intel Core i7-13700H, 16GB RAM DDR5, SSD 512GB NVMe, tela 15.6" 144Hz. Ideal para jogos e programação.',
    4599.90, 15, 'Informática', 2500,
    'https://images.unsplash.com/photo-1593640408182-31c228060e15?w=400'
),
(
    'Teclado Mecânico RGB',
    'Switch Cherry MX Red, retroiluminação RGB personalizável, layout ABNT2, cabo USB-C removível.',
    289.90, 50, 'Periféricos', 900,
    'https://images.unsplash.com/photo-1541140532154-b024d705b90a?w=400'
),
(
    'Monitor 27" 4K 144Hz',
    'Painel IPS, resolução 3840x2160, taxa de atualização 144Hz, HDR400, conexões HDMI 2.1 e DisplayPort 1.4.',
    2199.90, 8, 'Monitores', 5500,
    'https://images.unsplash.com/photo-1527443224154-c4a3942d3acf?w=400'
),
(
    'Mouse Gamer 25600 DPI',
    '11 botões programáveis, sensor óptico de alta precisão, peso ajustável, cabo trançado.',
    159.90, 100, 'Periféricos', 120,
    'https://images.unsplash.com/photo-1527814050087-3793815479db?w=400'
),
(
    'SSD NVMe 1TB Gen4',
    'Velocidade de leitura até 7400 MB/s, escrita até 6800 MB/s, interface PCIe 4.0 x4, M.2 2280.',
    449.90, 30, 'Armazenamento', 25,
    'https://images.unsplash.com/photo-1600262300518-5f03a1a2cb6c?w=400'
),
(
    'Headset Sem Fio 7.1',
    'Audio surround 7.1 virtual, microfone com cancelamento de ruído, bateria 30h, compatível com PC e console.',
    399.90, 20, 'Áudio', 350,
    'https://images.unsplash.com/photo-1583394838336-acd977736f90?w=400'
),
(
    'Webcam 4K 60fps',
    'Resolução 4K Ultra HD, 60fps, autofoco inteligente, microfone duplo estéreo, compatível com OBS e Meet.',
    599.90, 12, 'Periféricos', 210,
    'https://images.unsplash.com/photo-1611532736597-de2d4265fba3?w=400'
),
(
    'Cadeira Gamer Ergonômica',
    'Suporte lombar ajustável, apoio de braços 4D, reclinação 135°, rodízios silenciosos, capacidade 130kg.',
    1299.90, 5, 'Móveis', 22000,
    'https://images.unsplash.com/photo-1598300042247-d088f8ab3a91?w=400'
);
