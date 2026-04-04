-- PulsePlate local agent control plane (starter schema)

CREATE TABLE IF NOT EXISTS tasks (
  task_id TEXT PRIMARY KEY,
  track TEXT NOT NULL,
  owner TEXT NOT NULL,
  title TEXT NOT NULL,
  status TEXT NOT NULL,
  risk_class TEXT NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS action_packets (
  task_id TEXT PRIMARY KEY,
  packet_json TEXT NOT NULL,
  created_at TEXT NOT NULL,
  FOREIGN KEY(task_id) REFERENCES tasks(task_id)
);

CREATE TABLE IF NOT EXISTS agent_events (
  event_id TEXT PRIMARY KEY,
  task_id TEXT NOT NULL,
  agent_id TEXT NOT NULL,
  event_type TEXT NOT NULL,
  status TEXT NOT NULL,
  timestamp TEXT NOT NULL,
  event_json TEXT NOT NULL,
  FOREIGN KEY(task_id) REFERENCES tasks(task_id)
);

CREATE TABLE IF NOT EXISTS memory_capsules (
  capsule_id TEXT PRIMARY KEY,
  memory_type TEXT NOT NULL,
  title TEXT NOT NULL,
  summary TEXT NOT NULL,
  confidence REAL NOT NULL,
  promotion_status TEXT NOT NULL,
  sources_json TEXT NOT NULL,
  linked_task_id TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS approvals (
  approval_id TEXT PRIMARY KEY,
  task_id TEXT NOT NULL,
  risk_class TEXT NOT NULL,
  approver TEXT NOT NULL,
  decision TEXT NOT NULL,
  rationale TEXT,
  created_at TEXT NOT NULL,
  FOREIGN KEY(task_id) REFERENCES tasks(task_id)
);

CREATE INDEX IF NOT EXISTS idx_agent_events_task_id ON agent_events(task_id);
CREATE INDEX IF NOT EXISTS idx_memory_capsules_type ON memory_capsules(memory_type);
CREATE INDEX IF NOT EXISTS idx_approvals_task_id ON approvals(task_id);
