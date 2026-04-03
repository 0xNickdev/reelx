-- ============================================
-- REELX Database Schema
-- Run this in Supabase SQL Editor
-- ============================================

-- 1. ANALYSES (main table - stores all video analysis jobs)
CREATE TABLE IF NOT EXISTS analyses (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    job_id TEXT UNIQUE NOT NULL,
    user_id UUID NOT NULL,
    url TEXT NOT NULL,
    status TEXT DEFAULT 'pending',
    progress_percent INT DEFAULT 0,
    current_step TEXT DEFAULT 'В очереди…',
    video_meta JSONB,
    transcript TEXT,
    frames JSONB,
    script TEXT,
    hooks JSONB,
    description TEXT,
    hashtags JSONB,
    editor_brief TEXT,
    strategy TEXT,
    error TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS analyses_user_id_idx ON analyses(user_id);
CREATE INDEX IF NOT EXISTS analyses_job_id_idx ON analyses(job_id);
CREATE INDEX IF NOT EXISTS analyses_status_idx ON analyses(status);

-- 2. USER SETTINGS
CREATE TABLE IF NOT EXISTS user_settings (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID UNIQUE NOT NULL,
    language TEXT DEFAULT 'ru',
    about_me TEXT DEFAULT '',
    tone TEXT DEFAULT 'conversational',
    script_ending TEXT DEFAULT 'Подписывайся, чтобы не пропустить следующее.',
    description_ending TEXT DEFAULT '',
    stop_words TEXT DEFAULT '',
    video_format TEXT DEFAULT 'head_visual',
    interests JSONB DEFAULT '[]',
    telegram_id TEXT,
    trend_notifications BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS user_settings_user_id_idx ON user_settings(user_id);

-- 3. SUBSCRIPTIONS
CREATE TABLE IF NOT EXISTS subscriptions (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID UNIQUE NOT NULL,
    status TEXT DEFAULT 'none',  -- none | active | expired | cancelled
    started_at TIMESTAMPTZ,
    expires_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS subscriptions_user_id_idx ON subscriptions(user_id);
CREATE INDEX IF NOT EXISTS subscriptions_status_idx ON subscriptions(status);

-- 4. PAYMENTS
CREATE TABLE IF NOT EXISTS payments (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID NOT NULL,
    method TEXT NOT NULL,  -- yukassa | crypto
    external_id TEXT UNIQUE,
    amount NUMERIC NOT NULL,
    currency TEXT NOT NULL,
    status TEXT DEFAULT 'pending',  -- pending | paid | failed | refunded
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS payments_user_id_idx ON payments(user_id);
CREATE INDEX IF NOT EXISTS payments_status_idx ON payments(status);

-- 5. REFERRALS
CREATE TABLE IF NOT EXISTS referrals (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID UNIQUE NOT NULL,
    ref_code TEXT UNIQUE,
    status TEXT DEFAULT 'pending',  -- pending | approved | rejected
    commission_percent INT DEFAULT 15,
    instagram_username TEXT,
    instagram_followers INT,
    total_earned_rub NUMERIC DEFAULT 0,
    total_referrals INT DEFAULT 0,
    approved_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS referrals_ref_code_idx ON referrals(ref_code);

-- 6. REFERRAL CONVERSIONS (tracks who signed up via ref link)
CREATE TABLE IF NOT EXISTS referral_conversions (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    referrer_user_id UUID NOT NULL,
    referred_user_id UUID NOT NULL,
    ref_code TEXT NOT NULL,
    payment_id UUID,
    commission_rub NUMERIC DEFAULT 0,
    status TEXT DEFAULT 'pending',  -- pending | paid
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 7. TRENDS (populated by scraper)
CREATE TABLE IF NOT EXISTS trends (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    platform TEXT NOT NULL,       -- Instagram | TikTok | YouTube
    author TEXT NOT NULL,
    url TEXT UNIQUE NOT NULL,
    view_count BIGINT DEFAULT 0,
    like_count BIGINT DEFAULT 0,
    comment_count BIGINT DEFAULT 0,
    xfactor NUMERIC DEFAULT 0,    -- growth velocity score
    niche TEXT DEFAULT 'other',
    thumbnail_url TEXT,
    duration INT DEFAULT 0,
    published_at TIMESTAMPTZ,
    scraped_at TIMESTAMPTZ DEFAULT NOW(),
    is_active BOOLEAN DEFAULT TRUE
);
CREATE INDEX IF NOT EXISTS trends_platform_idx ON trends(platform);
CREATE INDEX IF NOT EXISTS trends_niche_idx ON trends(niche);
CREATE INDEX IF NOT EXISTS trends_xfactor_idx ON trends(xfactor DESC);

-- 8. Enable RLS (Row Level Security) — users see only their own data
ALTER TABLE analyses ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_settings ENABLE ROW LEVEL SECURITY;
ALTER TABLE subscriptions ENABLE ROW LEVEL SECURITY;
ALTER TABLE payments ENABLE ROW LEVEL SECURITY;

-- RLS Policies
CREATE POLICY "Users see own analyses" ON analyses FOR ALL USING (auth.uid() = user_id);
CREATE POLICY "Users see own settings" ON user_settings FOR ALL USING (auth.uid() = user_id);
CREATE POLICY "Users see own subscriptions" ON subscriptions FOR ALL USING (auth.uid() = user_id);
CREATE POLICY "Users see own payments" ON payments FOR ALL USING (auth.uid() = user_id);

-- Trends are public read
CREATE POLICY "Trends are public" ON trends FOR SELECT USING (true);

-- ============================================
-- Done! Run this SQL in Supabase SQL Editor
-- ============================================
