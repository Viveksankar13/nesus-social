BEGIN;

CREATE TABLE alembic_version (
    version_num VARCHAR(32) NOT NULL, 
    CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
);

-- Running upgrade  -> 0001_initial_schema

CREATE TABLE users (
    id UUID NOT NULL, 
    email VARCHAR(255) NOT NULL, 
    username VARCHAR(50) NOT NULL, 
    display_name VARCHAR(100) NOT NULL, 
    hashed_password VARCHAR(255) NOT NULL, 
    role VARCHAR(20) DEFAULT 'user' NOT NULL, 
    is_verified BOOLEAN DEFAULT false NOT NULL, 
    is_suspended BOOLEAN DEFAULT false NOT NULL, 
    bio TEXT, 
    location VARCHAR(100), 
    website VARCHAR(255), 
    avatar_url VARCHAR(500), 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    CONSTRAINT pk_users PRIMARY KEY (id), 
    CONSTRAINT uq_users_email UNIQUE (email), 
    CONSTRAINT uq_users_username UNIQUE (username)
);

CREATE UNIQUE INDEX ix_users_email ON users (email);

CREATE INDEX ix_users_id ON users (id);

CREATE UNIQUE INDEX ix_users_username ON users (username);

CREATE TABLE refresh_tokens (
    id UUID NOT NULL, 
    user_id UUID NOT NULL, 
    token_hash VARCHAR(64) NOT NULL, 
    family_id UUID NOT NULL, 
    user_agent VARCHAR(500), 
    ip_address VARCHAR(45), 
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    revoked BOOLEAN DEFAULT false NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    CONSTRAINT pk_refresh_tokens PRIMARY KEY (id), 
    CONSTRAINT fk_refresh_tokens_user_id_users FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE, 
    CONSTRAINT uq_refresh_tokens_token_hash UNIQUE (token_hash)
);

CREATE INDEX ix_refresh_tokens_family_id ON refresh_tokens (family_id);

CREATE INDEX ix_refresh_tokens_family_revoked ON refresh_tokens (family_id, revoked);

CREATE INDEX ix_refresh_tokens_id ON refresh_tokens (id);

CREATE UNIQUE INDEX ix_refresh_tokens_token_hash ON refresh_tokens (token_hash);

CREATE INDEX ix_refresh_tokens_user_id ON refresh_tokens (user_id);

CREATE TABLE email_tokens (
    id UUID NOT NULL, 
    user_id UUID NOT NULL, 
    token_hash VARCHAR(64) NOT NULL, 
    token_type VARCHAR(20) NOT NULL, 
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    used_at TIMESTAMP WITH TIME ZONE, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    CONSTRAINT pk_email_tokens PRIMARY KEY (id), 
    CONSTRAINT fk_email_tokens_user_id_users FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE, 
    CONSTRAINT uq_email_tokens_token_hash UNIQUE (token_hash)
);

CREATE INDEX ix_email_tokens_id ON email_tokens (id);

CREATE UNIQUE INDEX ix_email_tokens_token_hash ON email_tokens (token_hash);

CREATE INDEX ix_email_tokens_user_id ON email_tokens (user_id);

CREATE TABLE posts (
    id UUID NOT NULL, 
    author_id UUID NOT NULL, 
    content TEXT NOT NULL, 
    image_url VARCHAR(500), 
    is_hidden BOOLEAN DEFAULT false NOT NULL, 
    is_edited BOOLEAN DEFAULT false NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    CONSTRAINT pk_posts PRIMARY KEY (id), 
    CONSTRAINT ck_posts_ck_posts_content_length CHECK (length(content) <= 1000), 
    CONSTRAINT fk_posts_author_id_users FOREIGN KEY(author_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE INDEX ix_posts_author_id ON posts (author_id);

CREATE INDEX ix_posts_author_created_at ON posts (author_id, created_at);

CREATE INDEX ix_posts_feed_created_at ON posts (created_at);

CREATE INDEX ix_posts_id ON posts (id);

CREATE INDEX ix_posts_is_hidden ON posts (is_hidden);

CREATE TABLE comments (
    id UUID NOT NULL, 
    post_id UUID NOT NULL, 
    author_id UUID, 
    parent_id UUID, 
    content TEXT NOT NULL, 
    is_hidden BOOLEAN DEFAULT false NOT NULL, 
    is_edited BOOLEAN DEFAULT false NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    CONSTRAINT pk_comments PRIMARY KEY (id), 
    CONSTRAINT ck_comments_ck_comments_content_length CHECK (length(content) <= 500), 
    CONSTRAINT fk_comments_author_id_users FOREIGN KEY(author_id) REFERENCES users (id) ON DELETE SET NULL, 
    CONSTRAINT fk_comments_parent_id_comments FOREIGN KEY(parent_id) REFERENCES comments (id) ON DELETE CASCADE, 
    CONSTRAINT fk_comments_post_id_posts FOREIGN KEY(post_id) REFERENCES posts (id) ON DELETE CASCADE
);

CREATE INDEX ix_comments_author_id ON comments (author_id);

CREATE INDEX ix_comments_id ON comments (id);

CREATE INDEX ix_comments_is_hidden ON comments (is_hidden);

CREATE INDEX ix_comments_parent_id ON comments (parent_id);

CREATE INDEX ix_comments_post_created ON comments (post_id, created_at);

CREATE INDEX ix_comments_post_id ON comments (post_id);

CREATE TABLE likes (
    id UUID NOT NULL, 
    user_id UUID NOT NULL, 
    post_id UUID NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    CONSTRAINT pk_likes PRIMARY KEY (id), 
    CONSTRAINT fk_likes_post_id_posts FOREIGN KEY(post_id) REFERENCES posts (id) ON DELETE CASCADE, 
    CONSTRAINT fk_likes_user_id_users FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE, 
    CONSTRAINT uq_likes_user_post UNIQUE (user_id, post_id)
);

CREATE INDEX ix_likes_id ON likes (id);

CREATE INDEX ix_likes_post_id ON likes (post_id);

CREATE INDEX ix_likes_user_id ON likes (user_id);

CREATE TABLE notifications (
    id UUID NOT NULL, 
    user_id UUID NOT NULL, 
    type VARCHAR(50) NOT NULL, 
    payload JSONB NOT NULL, 
    is_read BOOLEAN DEFAULT false NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    CONSTRAINT pk_notifications PRIMARY KEY (id), 
    CONSTRAINT fk_notifications_user_id_users FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE INDEX ix_notifications_created_at ON notifications (created_at);

CREATE INDEX ix_notifications_id ON notifications (id);

CREATE INDEX ix_notifications_is_read ON notifications (is_read);

CREATE INDEX ix_notifications_user_id ON notifications (user_id);

CREATE INDEX ix_notifications_user_read ON notifications (user_id, is_read);

CREATE TABLE moderation_flags (
    id UUID NOT NULL, 
    content_type VARCHAR(20) NOT NULL, 
    content_id UUID NOT NULL, 
    category VARCHAR(50) NOT NULL, 
    severity VARCHAR(20) NOT NULL, 
    score FLOAT NOT NULL, 
    action VARCHAR(20) NOT NULL, 
    reason TEXT NOT NULL, 
    reviewed BOOLEAN DEFAULT false NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    CONSTRAINT pk_moderation_flags PRIMARY KEY (id)
);

CREATE INDEX ix_moderation_content ON moderation_flags (content_type, content_id);

CREATE INDEX ix_moderation_flags_content_id ON moderation_flags (content_id);

CREATE INDEX ix_moderation_flags_id ON moderation_flags (id);

CREATE INDEX ix_moderation_flags_reviewed ON moderation_flags (reviewed);

CREATE INDEX ix_moderation_queue ON moderation_flags (reviewed, action);

CREATE TABLE ai_chat_sessions (
    id UUID NOT NULL, 
    user_id UUID NOT NULL, 
    title VARCHAR(150) DEFAULT 'New Conversation' NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    CONSTRAINT pk_ai_chat_sessions PRIMARY KEY (id), 
    CONSTRAINT fk_ai_chat_sessions_user_id_users FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE INDEX ix_ai_chat_sessions_id ON ai_chat_sessions (id);

CREATE INDEX ix_ai_chat_sessions_user_id ON ai_chat_sessions (user_id);

CREATE TABLE ai_chat_messages (
    id UUID NOT NULL, 
    session_id UUID NOT NULL, 
    role VARCHAR(20) NOT NULL, 
    content TEXT NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    CONSTRAINT pk_ai_chat_messages PRIMARY KEY (id), 
    CONSTRAINT fk_ai_chat_messages_session_id_ai_chat_sessions FOREIGN KEY(session_id) REFERENCES ai_chat_sessions (id) ON DELETE CASCADE
);

CREATE INDEX ix_ai_chat_messages_id ON ai_chat_messages (id);

CREATE INDEX ix_ai_chat_messages_session_id ON ai_chat_messages (session_id);

CREATE TABLE ai_usage_logs (
    id UUID NOT NULL, 
    user_id UUID NOT NULL, 
    feature VARCHAR(50) NOT NULL, 
    latency_ms INTEGER NOT NULL, 
    tokens_used INTEGER DEFAULT 0 NOT NULL, 
    status VARCHAR(20) NOT NULL, 
    error TEXT, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    CONSTRAINT pk_ai_usage_logs PRIMARY KEY (id), 
    CONSTRAINT fk_ai_usage_logs_user_id_users FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE INDEX ix_ai_usage_feature_status ON ai_usage_logs (feature, status);

CREATE INDEX ix_ai_usage_user_date ON ai_usage_logs (user_id, created_at);

CREATE INDEX ix_ai_usage_logs_id ON ai_usage_logs (id);

CREATE INDEX ix_ai_usage_logs_user_id ON ai_usage_logs (user_id);

CREATE TABLE activity_logs (
    id UUID NOT NULL, 
    admin_id UUID, 
    action VARCHAR(50) NOT NULL, 
    resource_type VARCHAR(30) NOT NULL, 
    resource_id UUID, 
    details JSONB NOT NULL, 
    ip_address VARCHAR(45), 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    CONSTRAINT pk_activity_logs PRIMARY KEY (id), 
    CONSTRAINT fk_activity_logs_admin_id_users FOREIGN KEY(admin_id) REFERENCES users (id) ON DELETE SET NULL
);

CREATE INDEX ix_activity_admin_created ON activity_logs (admin_id, created_at);

CREATE INDEX ix_activity_logs_admin_id ON activity_logs (admin_id);

CREATE INDEX ix_activity_logs_id ON activity_logs (id);

CREATE INDEX ix_activity_resource ON activity_logs (resource_type, resource_id);

INSERT INTO alembic_version (version_num) VALUES ('0001_initial_schema') RETURNING alembic_version.version_num;

-- Running upgrade 0001_initial_schema -> 0002_add_student_usn

ALTER TABLE users ADD COLUMN usn VARCHAR(50);

CREATE UNIQUE INDEX ix_users_usn ON users (usn);

UPDATE alembic_version SET version_num='0002_add_student_usn' WHERE alembic_version.version_num = '0001_initial_schema';

-- Running upgrade 0002_add_student_usn -> 0003_add_friends_and_messages

CREATE TABLE friendships (
    id UUID NOT NULL, 
    sender_id UUID NOT NULL, 
    receiver_id UUID NOT NULL, 
    status VARCHAR(20) DEFAULT 'pending' NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    CONSTRAINT pk_friendships PRIMARY KEY (id), 
    CONSTRAINT fk_friendships_receiver_id_users FOREIGN KEY(receiver_id) REFERENCES users (id) ON DELETE CASCADE, 
    CONSTRAINT fk_friendships_sender_id_users FOREIGN KEY(sender_id) REFERENCES users (id) ON DELETE CASCADE, 
    CONSTRAINT uq_friendships_sender_receiver UNIQUE (sender_id, receiver_id)
);

CREATE INDEX ix_friendships_receiver_id ON friendships (receiver_id);

CREATE INDEX ix_friendships_sender_id ON friendships (sender_id);

CREATE INDEX ix_friendships_status ON friendships (status);

CREATE INDEX ix_friendships_status_receiver ON friendships (status, receiver_id);

CREATE INDEX ix_friendships_status_sender ON friendships (status, sender_id);

CREATE TABLE conversations (
    id UUID NOT NULL, 
    user1_id UUID NOT NULL, 
    user2_id UUID NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    CONSTRAINT pk_conversations PRIMARY KEY (id), 
    CONSTRAINT fk_conversations_user1_id_users FOREIGN KEY(user1_id) REFERENCES users (id) ON DELETE CASCADE, 
    CONSTRAINT fk_conversations_user2_id_users FOREIGN KEY(user2_id) REFERENCES users (id) ON DELETE CASCADE, 
    CONSTRAINT uq_conversations_user1_user2 UNIQUE (user1_id, user2_id)
);

CREATE INDEX ix_conversations_updated_at ON conversations (updated_at);

CREATE INDEX ix_conversations_user1_id ON conversations (user1_id);

CREATE INDEX ix_conversations_user2_id ON conversations (user2_id);

CREATE INDEX ix_conversations_users ON conversations (user1_id, user2_id);

CREATE TABLE direct_messages (
    id UUID NOT NULL, 
    conversation_id UUID NOT NULL, 
    sender_id UUID NOT NULL, 
    content TEXT NOT NULL, 
    is_read BOOLEAN DEFAULT false NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    CONSTRAINT pk_direct_messages PRIMARY KEY (id), 
    CONSTRAINT fk_direct_messages_conversation_id_conversations FOREIGN KEY(conversation_id) REFERENCES conversations (id) ON DELETE CASCADE, 
    CONSTRAINT fk_direct_messages_sender_id_users FOREIGN KEY(sender_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE INDEX ix_direct_messages_conversation_id ON direct_messages (conversation_id);

CREATE INDEX ix_direct_messages_created_at ON direct_messages (created_at);

CREATE INDEX ix_direct_messages_is_read ON direct_messages (is_read);

CREATE INDEX ix_direct_messages_sender_id ON direct_messages (sender_id);

UPDATE alembic_version SET version_num='0003_add_friends_and_messages' WHERE alembic_version.version_num = '0002_add_student_usn';

-- Running upgrade 0003_add_friends_and_messages -> 0004_add_skill_swap_economy

CREATE TABLE skills (
    id UUID NOT NULL, 
    slug VARCHAR(100) NOT NULL, 
    display_name VARCHAR(100) NOT NULL, 
    category VARCHAR(50) NOT NULL, 
    aliases JSONB NOT NULL, 
    status VARCHAR(20) DEFAULT 'active' NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    CONSTRAINT pk_skills PRIMARY KEY (id)
);

CREATE UNIQUE INDEX ix_skills_slug ON skills (slug);

CREATE INDEX ix_skills_category ON skills (category);

CREATE INDEX ix_skills_status ON skills (status);

CREATE TABLE user_skills (
    id UUID NOT NULL, 
    user_id UUID NOT NULL, 
    skill_id UUID NOT NULL, 
    skill_type VARCHAR(10) NOT NULL, 
    level VARCHAR(20) NOT NULL, 
    years_experience INTEGER, 
    notes TEXT, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    CONSTRAINT pk_user_skills PRIMARY KEY (id), 
    CONSTRAINT fk_user_skills_skill_id_skills FOREIGN KEY(skill_id) REFERENCES skills (id) ON DELETE CASCADE, 
    CONSTRAINT fk_user_skills_user_id_users FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE, 
    CONSTRAINT uq_user_skill_type UNIQUE (user_id, skill_id, skill_type)
);

CREATE INDEX ix_user_skills_user_id ON user_skills (user_id);

CREATE INDEX ix_user_skills_skill_id ON user_skills (skill_id);

CREATE INDEX ix_user_skills_skill_type ON user_skills (skill_type);

CREATE TABLE user_swap_profiles (
    id UUID NOT NULL, 
    user_id UUID NOT NULL, 
    bio TEXT, 
    coarse_lat FLOAT, 
    coarse_lng FLOAT, 
    area_label VARCHAR(150), 
    radius_km INTEGER DEFAULT '10' NOT NULL, 
    modes JSONB NOT NULL, 
    languages JSONB NOT NULL, 
    is_invisible BOOLEAN DEFAULT false NOT NULL, 
    accepts_newcomers BOOLEAN DEFAULT true NOT NULL, 
    is_18_confirmed BOOLEAN DEFAULT false NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    CONSTRAINT pk_user_swap_profiles PRIMARY KEY (id), 
    CONSTRAINT fk_user_swap_profiles_user_id_users FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE, 
    CONSTRAINT uq_user_swap_profiles_user_id UNIQUE (user_id)
);

CREATE INDEX ix_user_swap_profiles_user_id ON user_swap_profiles (user_id);

CREATE INDEX ix_swap_profiles_coarse_lat_lng ON user_swap_profiles (coarse_lat, coarse_lng);

CREATE TABLE availability_windows (
    id UUID NOT NULL, 
    user_id UUID NOT NULL, 
    day_of_week INTEGER NOT NULL, 
    start_time_utc VARCHAR(5) NOT NULL, 
    end_time_utc VARCHAR(5) NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    CONSTRAINT pk_availability_windows PRIMARY KEY (id), 
    CONSTRAINT fk_availability_windows_user_id_users FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE INDEX ix_availability_windows_user_id ON availability_windows (user_id);

CREATE INDEX ix_availability_windows_day_of_week ON availability_windows (day_of_week);

CREATE TABLE availability_blackouts (
    id UUID NOT NULL, 
    user_id UUID NOT NULL, 
    start_datetime_utc TIMESTAMP WITH TIME ZONE NOT NULL, 
    end_datetime_utc TIMESTAMP WITH TIME ZONE NOT NULL, 
    reason VARCHAR(255), 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    CONSTRAINT pk_availability_blackouts PRIMARY KEY (id), 
    CONSTRAINT fk_availability_blackouts_user_id_users FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE INDEX ix_availability_blackouts_user_id ON availability_blackouts (user_id);

CREATE INDEX ix_availability_blackouts_time ON availability_blackouts (start_datetime_utc, end_datetime_utc);

CREATE TABLE swap_listings (
    id UUID NOT NULL, 
    user_id UUID NOT NULL, 
    title VARCHAR(150) NOT NULL, 
    skill_offered_id UUID NOT NULL, 
    skill_wanted_id UUID, 
    description TEXT NOT NULL, 
    modes JSONB NOT NULL, 
    area_label VARCHAR(150), 
    status VARCHAR(20) DEFAULT 'active' NOT NULL, 
    tags JSONB NOT NULL, 
    expires_at TIMESTAMP WITH TIME ZONE, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    CONSTRAINT pk_swap_listings PRIMARY KEY (id), 
    CONSTRAINT fk_swap_listings_skill_offered_id_skills FOREIGN KEY(skill_offered_id) REFERENCES skills (id) ON DELETE RESTRICT, 
    CONSTRAINT fk_swap_listings_skill_wanted_id_skills FOREIGN KEY(skill_wanted_id) REFERENCES skills (id) ON DELETE SET NULL, 
    CONSTRAINT fk_swap_listings_user_id_users FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE INDEX ix_swap_listings_user_id ON swap_listings (user_id);

CREATE INDEX ix_swap_listings_status ON swap_listings (status);

CREATE INDEX ix_swap_listings_skill_offered_id ON swap_listings (skill_offered_id);

CREATE INDEX ix_swap_listings_skill_wanted_id ON swap_listings (skill_wanted_id);

CREATE INDEX ix_swap_listings_created_at ON swap_listings (created_at);

CREATE TABLE swap_requests (
    id UUID NOT NULL, 
    listing_id UUID, 
    requester_id UUID NOT NULL, 
    recipient_id UUID NOT NULL, 
    offered_skill_id UUID NOT NULL, 
    wanted_skill_id UUID NOT NULL, 
    mode VARCHAR(20) DEFAULT 'video' NOT NULL, 
    message VARCHAR(500) NOT NULL, 
    proposed_slots JSONB NOT NULL, 
    status VARCHAR(20) DEFAULT 'pending' NOT NULL, 
    counter_note VARCHAR(500), 
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    CONSTRAINT pk_swap_requests PRIMARY KEY (id), 
    CONSTRAINT fk_swap_requests_listing_id_swap_listings FOREIGN KEY(listing_id) REFERENCES swap_listings (id) ON DELETE SET NULL, 
    CONSTRAINT fk_swap_requests_offered_skill_id_skills FOREIGN KEY(offered_skill_id) REFERENCES skills (id) ON DELETE RESTRICT, 
    CONSTRAINT fk_swap_requests_recipient_id_users FOREIGN KEY(recipient_id) REFERENCES users (id) ON DELETE CASCADE, 
    CONSTRAINT fk_swap_requests_requester_id_users FOREIGN KEY(requester_id) REFERENCES users (id) ON DELETE CASCADE, 
    CONSTRAINT fk_swap_requests_wanted_skill_id_skills FOREIGN KEY(wanted_skill_id) REFERENCES skills (id) ON DELETE RESTRICT
);

CREATE INDEX ix_swap_requests_requester_id ON swap_requests (requester_id);

CREATE INDEX ix_swap_requests_recipient_id ON swap_requests (recipient_id);

CREATE INDEX ix_swap_requests_status ON swap_requests (status);

CREATE INDEX ix_swap_requests_expires_at ON swap_requests (expires_at);

CREATE TABLE swap_sessions (
    id UUID NOT NULL, 
    request_id UUID NOT NULL, 
    user_a_id UUID NOT NULL, 
    user_b_id UUID NOT NULL, 
    status VARCHAR(20) DEFAULT 'scheduled' NOT NULL, 
    mode VARCHAR(20) DEFAULT 'video' NOT NULL, 
    public_place_name VARCHAR(150), 
    public_place_address VARCHAR(255), 
    jitsi_room_token VARCHAR(100), 
    user_a_confirmed BOOLEAN DEFAULT false NOT NULL, 
    user_b_confirmed BOOLEAN DEFAULT false NOT NULL, 
    dispute_reason TEXT, 
    disputed_by_id UUID, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    CONSTRAINT pk_swap_sessions PRIMARY KEY (id), 
    CONSTRAINT fk_swap_sessions_disputed_by_id_users FOREIGN KEY(disputed_by_id) REFERENCES users (id) ON DELETE SET NULL, 
    CONSTRAINT fk_swap_sessions_request_id_swap_requests FOREIGN KEY(request_id) REFERENCES swap_requests (id) ON DELETE CASCADE, 
    CONSTRAINT fk_swap_sessions_user_a_id_users FOREIGN KEY(user_a_id) REFERENCES users (id) ON DELETE CASCADE, 
    CONSTRAINT fk_swap_sessions_user_b_id_users FOREIGN KEY(user_b_id) REFERENCES users (id) ON DELETE CASCADE, 
    CONSTRAINT uq_swap_sessions_request_id UNIQUE (request_id)
);

CREATE INDEX ix_swap_sessions_user_a_id ON swap_sessions (user_a_id);

CREATE INDEX ix_swap_sessions_user_b_id ON swap_sessions (user_b_id);

CREATE INDEX ix_swap_sessions_status ON swap_sessions (status);

CREATE TABLE swap_session_halves (
    id UUID NOT NULL, 
    session_id UUID NOT NULL, 
    half_number INTEGER NOT NULL, 
    mentor_id UUID NOT NULL, 
    learner_id UUID NOT NULL, 
    skill_id UUID NOT NULL, 
    start_time_utc TIMESTAMP WITH TIME ZONE NOT NULL, 
    end_time_utc TIMESTAMP WITH TIME ZONE NOT NULL, 
    status VARCHAR(20) DEFAULT 'scheduled' NOT NULL, 
    ics_uid VARCHAR(100) NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    CONSTRAINT pk_swap_session_halves PRIMARY KEY (id), 
    CONSTRAINT fk_swap_session_halves_learner_id_users FOREIGN KEY(learner_id) REFERENCES users (id) ON DELETE CASCADE, 
    CONSTRAINT fk_swap_session_halves_mentor_id_users FOREIGN KEY(mentor_id) REFERENCES users (id) ON DELETE CASCADE, 
    CONSTRAINT fk_swap_session_halves_session_id_swap_sessions FOREIGN KEY(session_id) REFERENCES swap_sessions (id) ON DELETE CASCADE, 
    CONSTRAINT fk_swap_session_halves_skill_id_skills FOREIGN KEY(skill_id) REFERENCES skills (id) ON DELETE RESTRICT
);

CREATE INDEX ix_swap_session_halves_session_id ON swap_session_halves (session_id);

CREATE INDEX ix_swap_session_halves_mentor_id ON swap_session_halves (mentor_id);

CREATE INDEX ix_swap_session_halves_learner_id ON swap_session_halves (learner_id);

CREATE INDEX ix_swap_session_halves_time ON swap_session_halves (start_time_utc, end_time_utc);

CREATE TABLE swap_messages (
    id UUID NOT NULL, 
    session_id UUID NOT NULL, 
    sender_id UUID NOT NULL, 
    content TEXT NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    CONSTRAINT pk_swap_messages PRIMARY KEY (id), 
    CONSTRAINT fk_swap_messages_sender_id_users FOREIGN KEY(sender_id) REFERENCES users (id) ON DELETE CASCADE, 
    CONSTRAINT fk_swap_messages_session_id_swap_sessions FOREIGN KEY(session_id) REFERENCES swap_sessions (id) ON DELETE CASCADE
);

CREATE INDEX ix_swap_messages_session_id ON swap_messages (session_id);

CREATE INDEX ix_swap_messages_sender_id ON swap_messages (sender_id);

CREATE INDEX ix_swap_messages_created_at ON swap_messages (created_at);

CREATE TABLE swap_reviews (
    id UUID NOT NULL, 
    session_id UUID NOT NULL, 
    reviewer_id UUID NOT NULL, 
    reviewee_id UUID NOT NULL, 
    rating INTEGER NOT NULL, 
    tags JSONB NOT NULL, 
    public_comment TEXT, 
    private_feedback TEXT, 
    is_revealed BOOLEAN DEFAULT false NOT NULL, 
    revealed_at TIMESTAMP WITH TIME ZONE, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    CONSTRAINT pk_swap_reviews PRIMARY KEY (id), 
    CONSTRAINT fk_swap_reviews_reviewee_id_users FOREIGN KEY(reviewee_id) REFERENCES users (id) ON DELETE CASCADE, 
    CONSTRAINT fk_swap_reviews_reviewer_id_users FOREIGN KEY(reviewer_id) REFERENCES users (id) ON DELETE CASCADE, 
    CONSTRAINT fk_swap_reviews_session_id_swap_sessions FOREIGN KEY(session_id) REFERENCES swap_sessions (id) ON DELETE CASCADE, 
    CONSTRAINT uq_session_reviewer UNIQUE (session_id, reviewer_id)
);

CREATE INDEX ix_swap_reviews_session_id ON swap_reviews (session_id);

CREATE INDEX ix_swap_reviews_reviewer_id ON swap_reviews (reviewer_id);

CREATE INDEX ix_swap_reviews_reviewee_id ON swap_reviews (reviewee_id);

CREATE INDEX ix_swap_reviews_is_revealed ON swap_reviews (is_revealed);

CREATE TABLE user_blocks (
    id UUID NOT NULL, 
    blocker_id UUID NOT NULL, 
    blocked_id UUID NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    CONSTRAINT pk_user_blocks PRIMARY KEY (id), 
    CONSTRAINT fk_user_blocks_blocked_id_users FOREIGN KEY(blocked_id) REFERENCES users (id) ON DELETE CASCADE, 
    CONSTRAINT fk_user_blocks_blocker_id_users FOREIGN KEY(blocker_id) REFERENCES users (id) ON DELETE CASCADE, 
    CONSTRAINT uq_user_blocks_pair UNIQUE (blocker_id, blocked_id)
);

CREATE INDEX ix_user_blocks_blocker_id ON user_blocks (blocker_id);

CREATE INDEX ix_user_blocks_blocked_id ON user_blocks (blocked_id);

CREATE TABLE swap_reports (
    id UUID NOT NULL, 
    reporter_id UUID NOT NULL, 
    target_type VARCHAR(20) NOT NULL, 
    target_id UUID NOT NULL, 
    category VARCHAR(50) NOT NULL, 
    notes TEXT, 
    status VARCHAR(20) DEFAULT 'pending' NOT NULL, 
    admin_resolution TEXT, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    CONSTRAINT pk_swap_reports PRIMARY KEY (id), 
    CONSTRAINT fk_swap_reports_reporter_id_users FOREIGN KEY(reporter_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE INDEX ix_swap_reports_reporter_id ON swap_reports (reporter_id);

CREATE INDEX ix_swap_reports_target_id ON swap_reports (target_id);

CREATE INDEX ix_swap_reports_status ON swap_reports (status);

CREATE TABLE trust_scores (
    id UUID NOT NULL, 
    user_id UUID NOT NULL, 
    score INTEGER DEFAULT '100' NOT NULL, 
    completed_count INTEGER DEFAULT '0' NOT NULL, 
    no_show_count INTEGER DEFAULT '0' NOT NULL, 
    cancellation_count INTEGER DEFAULT '0' NOT NULL, 
    avg_rating FLOAT DEFAULT '5.0' NOT NULL, 
    badges JSONB NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    CONSTRAINT pk_trust_scores PRIMARY KEY (id), 
    CONSTRAINT fk_trust_scores_user_id_users FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE, 
    CONSTRAINT uq_trust_scores_user_id UNIQUE (user_id)
);

CREATE INDEX ix_trust_scores_user_id ON trust_scores (user_id);

CREATE TABLE reciprocity_ledger (
    id UUID NOT NULL, 
    user_id UUID NOT NULL, 
    minutes_taught INTEGER DEFAULT '0' NOT NULL, 
    minutes_learned INTEGER DEFAULT '0' NOT NULL, 
    net_balance_minutes INTEGER DEFAULT '0' NOT NULL, 
    grace_used INTEGER DEFAULT '0' NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    CONSTRAINT pk_reciprocity_ledger PRIMARY KEY (id), 
    CONSTRAINT fk_reciprocity_ledger_user_id_users FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE, 
    CONSTRAINT uq_reciprocity_ledger_user_id UNIQUE (user_id)
);

CREATE INDEX ix_reciprocity_ledger_user_id ON reciprocity_ledger (user_id);

CREATE TABLE match_explanations (
    id UUID NOT NULL, 
    user_a_id UUID NOT NULL, 
    user_b_id UUID NOT NULL, 
    input_hash VARCHAR(64) NOT NULL, 
    explanation TEXT NOT NULL, 
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    CONSTRAINT pk_match_explanations PRIMARY KEY (id), 
    CONSTRAINT fk_match_explanations_user_a_id_users FOREIGN KEY(user_a_id) REFERENCES users (id) ON DELETE CASCADE, 
    CONSTRAINT fk_match_explanations_user_b_id_users FOREIGN KEY(user_b_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE INDEX ix_match_explanations_input_hash ON match_explanations (input_hash);

CREATE INDEX ix_match_explanations_users ON match_explanations (user_a_id, user_b_id);

CREATE TABLE job_runs (
    id UUID NOT NULL, 
    job_name VARCHAR(100) NOT NULL, 
    status VARCHAR(20) DEFAULT 'running' NOT NULL, 
    records_processed INTEGER DEFAULT '0' NOT NULL, 
    details JSONB, 
    started_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    completed_at TIMESTAMP WITH TIME ZONE, 
    CONSTRAINT pk_job_runs PRIMARY KEY (id)
);

CREATE INDEX ix_job_runs_job_name ON job_runs (job_name);

UPDATE alembic_version SET version_num='0004_add_skill_swap_economy' WHERE alembic_version.version_num = '0003_add_friends_and_messages';

COMMIT;

