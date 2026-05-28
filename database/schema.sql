CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE schools (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    city VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    lessons_url_parallel_a TEXT,
    lessons_url_parallel_b TEXT,
    lessons_url_school TEXT
);

CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(255),
    role VARCHAR(20) NOT NULL CHECK (role IN ('admin', 'user')),
    staff_scope VARCHAR(20) CHECK (staff_scope IS NULL OR staff_scope IN ('parallel_a', 'parallel_b', 'school', 'support')),
    stem_specialty VARCHAR(1) CHECK (stem_specialty IS NULL OR stem_specialty IN ('S', 'T', 'E', 'M')),
    school_id UUID REFERENCES schools(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    email_verified BOOLEAN NOT NULL DEFAULT TRUE,
    email_verification_token VARCHAR(128)
);

CREATE TABLE classes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    school_id UUID NOT NULL REFERENCES schools(id),
    name VARCHAR(50) NOT NULL,
    grade INT NOT NULL,
    teacher_id UUID REFERENCES users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    moodle_survey_enabled BOOLEAN NOT NULL DEFAULT false,
    moodle_survey_url TEXT,
    UNIQUE(school_id, name)
);

CREATE TABLE teacher_class_assignments (
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    class_id UUID NOT NULL REFERENCES classes(id) ON DELETE CASCADE,
    PRIMARY KEY (user_id, class_id)
);

CREATE TABLE class_students (
    class_id UUID REFERENCES classes(id),
    student_id UUID REFERENCES users(id),
    PRIMARY KEY (class_id, student_id)
);

CREATE TABLE surveys (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    school_year VARCHAR(20),
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    closed_at TIMESTAMP,
    is_active BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE survey_responses (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    survey_id UUID NOT NULL REFERENCES surveys(id),
    student_id UUID NOT NULL REFERENCES users(id),
    class_id UUID REFERENCES classes(id),
    submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(survey_id, student_id)
);

CREATE TABLE survey_answers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    response_id UUID NOT NULL REFERENCES survey_responses(id),
    question_code VARCHAR(10) NOT NULL,
    value INT NOT NULL CHECK (value >= 1 AND value <= 7)
);

CREATE TABLE class_models (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    class_id UUID NOT NULL REFERENCES classes(id),
    survey_id UUID NOT NULL REFERENCES surveys(id),
    s_avg DECIMAL(5,2),
    t_avg DECIMAL(5,2),
    e_avg DECIMAL(5,2),
    m_avg DECIMAL(5,2),
    ranking VARCHAR(20),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(class_id, survey_id)
);

CREATE TABLE login_attempts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) NOT NULL,
    ip_address INET,
    success BOOLEAN,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_role ON users(role);
CREATE INDEX idx_users_school ON users(school_id);
CREATE INDEX idx_survey_responses_survey ON survey_responses(survey_id);
CREATE INDEX idx_survey_responses_student ON survey_responses(student_id);
CREATE INDEX idx_survey_answers_response ON survey_answers(response_id);
CREATE INDEX idx_class_models_class ON class_models(class_id);
CREATE INDEX idx_login_attempts_email ON login_attempts(email);
CREATE INDEX idx_login_attempts_created ON login_attempts(created_at);
