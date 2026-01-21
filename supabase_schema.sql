-- 흑백요리사2 Supabase 테이블 스키마
-- 실행: Supabase Dashboard > SQL Editor

-- =====================================================
-- 1. 서울시 유동인구 테이블
-- =====================================================
CREATE TABLE IF NOT EXISTS seoul_floating_population (
    id BIGSERIAL PRIMARY KEY,
    sensing_time TIMESTAMP NOT NULL,
    autonomous_district VARCHAR(50) NOT NULL,  -- 자치구
    administrative_district VARCHAR(100),       -- 행정동
    visitor_count INTEGER DEFAULT 0,
    reg_dttm VARCHAR(50),
    created_at TIMESTAMP DEFAULT NOW(),
    
    -- 인덱스용 컬럼 제약
    CONSTRAINT unique_sensing_district UNIQUE (sensing_time, autonomous_district, administrative_district)
);

-- 인덱스 생성
CREATE INDEX IF NOT EXISTS idx_pop_sensing_time ON seoul_floating_population(sensing_time);
CREATE INDEX IF NOT EXISTS idx_pop_district ON seoul_floating_population(autonomous_district);
CREATE INDEX IF NOT EXISTS idx_pop_created_at ON seoul_floating_population(created_at);


-- =====================================================
-- 2. 캐치테이블 리뷰 테이블
-- =====================================================
CREATE TABLE IF NOT EXISTS catchtable_reviews (
    id BIGSERIAL PRIMARY KEY,
    restaurant_name VARCHAR(200) NOT NULL,
    chef_info VARCHAR(100),
    category VARCHAR(100),
    review_count INTEGER DEFAULT 0,
    previous_count INTEGER DEFAULT 0,
    change_count INTEGER DEFAULT 0,
    collected_at TIMESTAMP NOT NULL,
    url TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- 인덱스 생성
CREATE INDEX IF NOT EXISTS idx_reviews_restaurant ON catchtable_reviews(restaurant_name);
CREATE INDEX IF NOT EXISTS idx_reviews_collected_at ON catchtable_reviews(collected_at);
CREATE INDEX IF NOT EXISTS idx_reviews_chef ON catchtable_reviews(chef_info);


-- =====================================================
-- 3. 리뷰 히스토리 뷰 (일별 변화 추적용)
-- =====================================================
CREATE OR REPLACE VIEW review_daily_changes AS
SELECT 
    restaurant_name,
    chef_info,
    category,
    DATE(collected_at) as collected_date,
    review_count,
    previous_count,
    change_count,
    CASE 
        WHEN previous_count > 0 THEN 
            ROUND(((review_count - previous_count)::NUMERIC / previous_count) * 100, 2)
        ELSE 0 
    END as change_rate_percent
FROM catchtable_reviews
ORDER BY collected_at DESC;


-- =====================================================
-- 4. 자치구별 유동인구 일별 집계 뷰
-- =====================================================
CREATE OR REPLACE VIEW population_daily_summary AS
SELECT 
    DATE(sensing_time) as date,
    autonomous_district as district,
    SUM(visitor_count) as total_visitors,
    AVG(visitor_count) as avg_visitors,
    MAX(visitor_count) as max_visitors,
    COUNT(*) as record_count
FROM seoul_floating_population
GROUP BY DATE(sensing_time), autonomous_district
ORDER BY date DESC, district;


-- =====================================================
-- RLS (Row Level Security) 설정 (선택사항)
-- =====================================================
-- ALTER TABLE seoul_floating_population ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE catchtable_reviews ENABLE ROW LEVEL SECURITY;

-- 읽기 전용 정책 (모든 사용자)
-- CREATE POLICY "Public read access" ON seoul_floating_population FOR SELECT USING (true);
-- CREATE POLICY "Public read access" ON catchtable_reviews FOR SELECT USING (true);
