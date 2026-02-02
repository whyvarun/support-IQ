-- Enable pgvector extension for vector embeddings
CREATE EXTENSION IF NOT EXISTS vector;

-- Create enum for ticket status
CREATE TYPE ticket_status AS ENUM ('open', 'in_progress', 'resolved', 'closed', 'escalated');

-- Create enum for knowledge tier
CREATE TYPE knowledge_tier AS ENUM ('L1', 'L2', 'L3');

-- Create enum for urgency level
CREATE TYPE urgency_level AS ENUM ('low', 'medium', 'high', 'critical');

-- Tickets table: stores all support tickets
CREATE TABLE IF NOT EXISTS tickets (
    id SERIAL PRIMARY KEY,
    title VARCHAR(500) NOT NULL,
    description TEXT NOT NULL,
    status ticket_status DEFAULT 'open',
    urgency_score INTEGER CHECK (urgency_score >= 1 AND urgency_score <= 10),
    urgency_level urgency_level DEFAULT 'medium',
    sentiment_score FLOAT,
    sentiment_label VARCHAR(50),
    category VARCHAR(100),
    assigned_tier knowledge_tier DEFAULT 'L1',
    user_email VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    resolved_at TIMESTAMP WITH TIME ZONE
);

-- Ticket embeddings for semantic search
CREATE TABLE IF NOT EXISTS ticket_embeddings (
    id SERIAL PRIMARY KEY,
    ticket_id INTEGER REFERENCES tickets(id) ON DELETE CASCADE,
    embedding vector(384),  -- MiniLM-L6 produces 384-dim embeddings
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Resolutions table: stores solutions and feedback
CREATE TABLE IF NOT EXISTS resolutions (
    id SERIAL PRIMARY KEY,
    ticket_id INTEGER REFERENCES tickets(id) ON DELETE CASCADE,
    solution TEXT NOT NULL,
    resolution_source VARCHAR(100),  -- 'L1_KB', 'L2_KB', 'L3_KB', 'manual'
    resolution_time_minutes INTEGER,
    feedback_score INTEGER CHECK (feedback_score >= 1 AND feedback_score <= 5),
    feedback_comment TEXT,
    resolved_by VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Knowledge base: tiered knowledge storage
CREATE TABLE IF NOT EXISTS knowledge_base (
    id SERIAL PRIMARY KEY,
    tier knowledge_tier NOT NULL,
    title VARCHAR(500) NOT NULL,
    content TEXT NOT NULL,
    keywords TEXT[],
    category VARCHAR(100),
    usage_count INTEGER DEFAULT 0,
    success_rate FLOAT DEFAULT 0.0,
    avg_feedback_score FLOAT DEFAULT 0.0,
    embedding vector(384),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Promotion history: tracks auto-promotion of knowledge items
CREATE TABLE IF NOT EXISTS promotion_history (
    id SERIAL PRIMARY KEY,
    knowledge_id INTEGER REFERENCES knowledge_base(id) ON DELETE CASCADE,
    from_tier knowledge_tier NOT NULL,
    to_tier knowledge_tier NOT NULL,
    reason TEXT,
    usage_count_at_promotion INTEGER,
    avg_feedback_at_promotion FLOAT,
    promoted_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for performance
CREATE INDEX idx_tickets_status ON tickets(status);
CREATE INDEX idx_tickets_urgency ON tickets(urgency_score DESC);
CREATE INDEX idx_tickets_created ON tickets(created_at DESC);
CREATE INDEX idx_kb_tier ON knowledge_base(tier);
CREATE INDEX idx_kb_category ON knowledge_base(category);
CREATE INDEX idx_ticket_embedding ON ticket_embeddings USING ivfflat (embedding vector_cosine_ops);
CREATE INDEX idx_kb_embedding ON knowledge_base USING ivfflat (embedding vector_cosine_ops);

-- Full-text search index for hybrid search
CREATE INDEX idx_tickets_fts ON tickets USING gin(to_tsvector('english', title || ' ' || description));
CREATE INDEX idx_kb_fts ON knowledge_base USING gin(to_tsvector('english', title || ' ' || content));

-- Insert sample L1 knowledge base entries (FAQ/Common Issues)
INSERT INTO knowledge_base (tier, title, content, keywords, category) VALUES
('L1', 'Password Reset Procedure', 'To reset your password: 1. Go to login page 2. Click "Forgot Password" 3. Enter your email 4. Check inbox for reset link 5. Create new password meeting requirements (8+ chars, 1 number, 1 special char)', ARRAY['password', 'reset', 'forgot', 'login', 'access'], 'authentication'),
('L1', 'Email Not Receiving Messages', 'If you are not receiving emails: 1. Check spam/junk folder 2. Verify email address spelling 3. Check storage quota 4. Whitelist our domain 5. Try incognito mode', ARRAY['email', 'not receiving', 'spam', 'inbox', 'messages'], 'email'),
('L1', 'VPN Connection Issues', 'VPN troubleshooting steps: 1. Restart VPN client 2. Check internet connection 3. Try different VPN server 4. Clear VPN cache 5. Reinstall VPN client if issues persist', ARRAY['vpn', 'connection', 'network', 'remote', 'access'], 'network'),
('L1', 'Slow Computer Performance', 'To improve computer performance: 1. Restart computer 2. Close unnecessary programs 3. Clear temporary files 4. Check for malware 5. Ensure adequate disk space (>10% free)', ARRAY['slow', 'performance', 'computer', 'speed', 'lag'], 'hardware'),
('L1', 'Printer Not Working', 'Printer troubleshooting: 1. Check printer is powered on 2. Verify cable connections 3. Check paper and ink levels 4. Restart print spooler service 5. Reinstall printer drivers', ARRAY['printer', 'printing', 'not working', 'paper', 'jam'], 'hardware');

-- Insert sample L2 knowledge base entries (Technical Guides)
INSERT INTO knowledge_base (tier, title, content, keywords, category) VALUES
('L2', 'Active Directory Account Lockout', 'For AD account lockouts: 1. Use Account Lockout Status tool 2. Identify source of lockouts via Event Viewer 3. Check for cached credentials 4. Review scheduled tasks with old passwords 5. Check mobile devices with corporate email', ARRAY['active directory', 'lockout', 'account', 'ad', 'security'], 'authentication'),
('L2', 'Exchange Online Mailbox Recovery', 'To recover deleted mailbox items: 1. Check Recoverable Items folder 2. Use Compliance Center eDiscovery 3. If within retention period, use PowerShell: Get-RecoverableItems 4. Restore from backup if beyond retention', ARRAY['exchange', 'mailbox', 'recovery', 'deleted', 'restore'], 'email'),
('L2', 'Network Drive Mapping Issues', 'Resolve network drive issues: 1. Check network connectivity 2. Verify user permissions in AD 3. Test UNC path directly 4. Clear cached credentials: rundll32.exe keymgr.dll KRShowKeyMgr 5. Recreate drive mapping via GPO', ARRAY['network drive', 'mapping', 'unc', 'permissions', 'share'], 'network'),
('L2', 'SSL Certificate Errors', 'For SSL certificate errors: 1. Verify certificate validity dates 2. Check certificate chain 3. Ensure correct hostname matching 4. Update root CA certificates 5. Check for proxy interference', ARRAY['ssl', 'certificate', 'https', 'security', 'tls'], 'security'),
('L2', 'Database Connection Timeout', 'For database timeout issues: 1. Check connection pool settings 2. Verify network latency to DB server 3. Review long-running queries 4. Increase connection timeout value 5. Check for connection leaks in application', ARRAY['database', 'timeout', 'connection', 'sql', 'pool'], 'database');

-- Insert sample L3 knowledge base entries (Expert Solutions)
INSERT INTO knowledge_base (tier, title, content, keywords, category) VALUES
('L3', 'Kerberos Authentication Failures', 'Advanced Kerberos troubleshooting: 1. Verify time sync (max 5min skew) 2. Check SPN registration: setspn -L 3. Review Kerberos event logs 4. Test with klist tickets 5. Verify KDC reachability 6. Check delegation settings for multi-hop', ARRAY['kerberos', 'authentication', 'spn', 'kdc', 'delegation'], 'authentication'),
('L3', 'Exchange Hybrid Mail Flow Issues', 'For hybrid mail flow problems: 1. Verify connectors in EAC and on-prem 2. Check certificate on send/receive connectors 3. Test with Remote Connectivity Analyzer 4. Review message tracking logs 5. Check MX and SPF records 6. Verify OAuth configuration', ARRAY['exchange', 'hybrid', 'mail flow', 'connector', 'o365'], 'email'),
('L3', 'Payment Processing System Errors', 'Critical payment system troubleshooting: 1. Check payment gateway status page 2. Verify API credentials and endpoints 3. Review transaction logs for error codes 4. Check SSL/TLS version compatibility 5. Verify PCI compliance settings 6. Escalate to payment provider if gateway issue', ARRAY['payment', 'processing', 'transaction', 'gateway', 'error', 'critical'], 'payment'),
('L3', 'Data Replication Lag in Distributed Systems', 'For replication lag issues: 1. Monitor replication latency metrics 2. Check network bandwidth between nodes 3. Review write throughput vs capacity 4. Analyze log shipping delays 5. Consider read replica scaling 6. Implement eventual consistency patterns', ARRAY['replication', 'lag', 'distributed', 'sync', 'database'], 'database'),
('L3', 'Zero-Day Security Incident Response', 'For potential zero-day incidents: 1. Isolate affected systems immediately 2. Capture memory dumps and logs 3. Contact security vendor for IOCs 4. Implement network segmentation 5. Deploy emergency patches/workarounds 6. Conduct forensic analysis 7. Report to CISO and legal', ARRAY['security', 'zero-day', 'incident', 'breach', 'forensic', 'critical'], 'security');

-- Create function to update timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers for updated_at
CREATE TRIGGER update_tickets_updated_at BEFORE UPDATE ON tickets
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_knowledge_base_updated_at BEFORE UPDATE ON knowledge_base
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
