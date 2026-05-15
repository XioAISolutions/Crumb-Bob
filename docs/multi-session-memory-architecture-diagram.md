# Multi-Session Memory System - Architecture Diagrams

This document contains visual representations of the Multi-Session Memory System architecture using Mermaid diagrams.

---

## 1. System Architecture Overview

```mermaid
graph TB
    subgraph "Input Layer"
        BR[Bob Report]
        GD[Git Diff]
        TO[Test Output]
        RN[Repo Notes]
    end
    
    subgraph "CrumbBob Core"
        Parser[Parser]
        Packer[Packer]
        Validator[Validator]
    end
    
    subgraph "Memory Layer NEW"
        Recorder[Session Recorder]
        DB[(SQLite Database)]
        QueryAPI[Query API]
        Intelligence[Intelligence Engine]
    end
    
    subgraph "Output Layer"
        Pack[Pack Files]
        Insights[Insights]
        Predictions[Predictions]
        Dashboard[Team Dashboard]
    end
    
    BR --> Parser
    GD --> Parser
    TO --> Parser
    RN --> Parser
    
    Parser --> Packer
    Packer --> Pack
    Packer --> Validator
    
    Pack --> Recorder
    Recorder --> DB
    
    DB --> QueryAPI
    DB --> Intelligence
    
    QueryAPI --> Insights
    Intelligence --> Predictions
    QueryAPI --> Dashboard
    
    style DB fill:#f9f,stroke:#333,stroke-width:4px
    style Intelligence fill:#bbf,stroke:#333,stroke-width:2px
    style Recorder fill:#bfb,stroke:#333,stroke-width:2px
```

---

## 2. Database Schema Relationships

```mermaid
erDiagram
    sessions ||--o{ packs : generates
    sessions ||--o{ session_files : mentions
    sessions ||--o{ session_commands : uses
    sessions ||--o{ session_risks : identifies
    sessions ||--o{ session_tasks : creates
    sessions ||--o| sessions : parent_of
    
    files ||--o{ session_files : mentioned_in
    files ||--o{ relationships : relates_to
    
    commands ||--o{ session_commands : used_in
    
    risks ||--o{ session_risks : appears_in
    
    tasks ||--o{ session_tasks : tracked_in
    
    sessions {
        string id PK
        string timestamp
        string title
        string bob_report_hash
        string parent_session_id FK
        string branch_name
        string commit_hash
        string author
    }
    
    packs {
        string id PK
        string session_id FK
        int file_count
        int risk_count
        int task_count
        string validation_status
    }
    
    files {
        int id PK
        string file_path
        string first_seen_session FK
        string last_seen_session FK
        int mention_count
    }
    
    risks {
        int id PK
        string risk_text
        string status
        string severity
        string category
        int mention_count
    }
    
    tasks {
        int id PK
        string task_text
        string status
        string priority
        float completion_time_days
    }
    
    relationships {
        int id PK
        int file1_id FK
        int file2_id FK
        int co_change_count
        float confidence
    }
```

---

## 3. Data Flow: Recording a Session

```mermaid
sequenceDiagram
    participant User
    participant CLI
    participant Recorder
    participant Parser
    participant DB
    participant Git
    participant Intelligence
    
    User->>CLI: crumdbob record ./pack
    CLI->>Recorder: record_pack(pack_dir)
    
    Recorder->>Parser: parse_pack(pack_dir)
    Parser-->>Recorder: pack_data
    
    Recorder->>Git: get_context()
    Git-->>Recorder: branch, commit, author
    
    Recorder->>DB: INSERT session
    Recorder->>DB: INSERT pack metadata
    
    loop For each file
        Recorder->>DB: INSERT/UPDATE file
        Recorder->>DB: INSERT session_file link
    end
    
    loop For each risk
        Recorder->>DB: INSERT/UPDATE risk
        Recorder->>DB: INSERT session_risk link
    end
    
    loop For each task
        Recorder->>DB: INSERT/UPDATE task
        Recorder->>DB: INSERT session_task link
    end
    
    Recorder->>DB: UPDATE relationships
    
    Recorder->>Intelligence: detect_patterns()
    Intelligence->>DB: INSERT insights
    
    DB-->>Recorder: session_id
    Recorder-->>CLI: success
    CLI-->>User: Session recorded!
```

---

## 4. Query Processing Flow

```mermaid
graph LR
    subgraph "User Input"
        NLQ[Natural Language Query]
        SQ[Structured Query]
        SQL[Direct SQL]
    end
    
    subgraph "Query Layer"
        Translator[NL Translator]
        QueryBuilder[Query Builder]
        SQLExecutor[SQL Executor]
    end
    
    subgraph "Database"
        Tables[(Tables)]
        Views[(Views)]
        Indexes[(Indexes)]
    end
    
    subgraph "Output"
        Results[Query Results]
        Formatted[Formatted Output]
        JSON[JSON Export]
    end
    
    NLQ --> Translator
    SQ --> QueryBuilder
    SQL --> SQLExecutor
    
    Translator --> SQLExecutor
    QueryBuilder --> SQLExecutor
    
    SQLExecutor --> Tables
    SQLExecutor --> Views
    Tables --> Indexes
    
    Tables --> Results
    Views --> Results
    
    Results --> Formatted
    Results --> JSON
    
    style Translator fill:#bbf
    style Tables fill:#f9f
```

---

## 5. Intelligence Engine Architecture

```mermaid
graph TB
    subgraph "Data Sources"
        Sessions[Sessions History]
        Files[File Mentions]
        Risks[Risk History]
        Tasks[Task History]
        Relationships[File Relationships]
    end
    
    subgraph "Intelligence Engine"
        PatternDetector[Pattern Detector]
        ImpactPredictor[Impact Predictor]
        TrendAnalyzer[Trend Analyzer]
        AnomalyDetector[Anomaly Detector]
    end
    
    subgraph "Algorithms"
        Clustering[Clustering]
        TimeSeries[Time Series Analysis]
        ML[Machine Learning]
        Statistics[Statistical Analysis]
    end
    
    subgraph "Outputs"
        Patterns[Detected Patterns]
        Predictions[Impact Predictions]
        Trends[Trend Reports]
        Anomalies[Anomaly Alerts]
        Insights[Generated Insights]
    end
    
    Sessions --> PatternDetector
    Files --> PatternDetector
    Risks --> PatternDetector
    
    Files --> ImpactPredictor
    Relationships --> ImpactPredictor
    Risks --> ImpactPredictor
    
    Sessions --> TrendAnalyzer
    Risks --> TrendAnalyzer
    Tasks --> TrendAnalyzer
    
    Sessions --> AnomalyDetector
    Risks --> AnomalyDetector
    Files --> AnomalyDetector
    
    PatternDetector --> Clustering
    ImpactPredictor --> ML
    TrendAnalyzer --> TimeSeries
    AnomalyDetector --> Statistics
    
    Clustering --> Patterns
    ML --> Predictions
    TimeSeries --> Trends
    Statistics --> Anomalies
    
    Patterns --> Insights
    Predictions --> Insights
    Trends --> Insights
    Anomalies --> Insights
    
    style PatternDetector fill:#bbf
    style ImpactPredictor fill:#bfb
    style TrendAnalyzer fill:#fbb
    style AnomalyDetector fill:#ffb
```

---

## 6. Team Collaboration Flow

```mermaid
graph TB
    subgraph "Developer A"
        A_Bob[Bob Session]
        A_Pack[Generate Pack]
        A_Record[Record to DB]
    end
    
    subgraph "Developer B"
        B_Bob[Bob Session]
        B_Pack[Generate Pack]
        B_Record[Record to DB]
    end
    
    subgraph "Developer C"
        C_Query[Query History]
        C_Insights[View Insights]
        C_Predict[Get Predictions]
    end
    
    subgraph "Shared Memory"
        SharedDB[(Team Database)]
        Sync[Sync Service]
    end
    
    subgraph "Team Dashboard"
        Timeline[Session Timeline]
        RiskMap[Risk Heatmap]
        Metrics[Team Metrics]
        Activity[File Activity]
    end
    
    A_Bob --> A_Pack
    A_Pack --> A_Record
    A_Record --> SharedDB
    
    B_Bob --> B_Pack
    B_Pack --> B_Record
    B_Record --> SharedDB
    
    SharedDB --> Sync
    Sync --> SharedDB
    
    C_Query --> SharedDB
    C_Insights --> SharedDB
    C_Predict --> SharedDB
    
    SharedDB --> Timeline
    SharedDB --> RiskMap
    SharedDB --> Metrics
    SharedDB --> Activity
    
    style SharedDB fill:#f9f,stroke:#333,stroke-width:4px
    style Sync fill:#bfb
```

---

## 7. Integration Points

```mermaid
graph LR
    subgraph "CrumbBob Memory"
        Core[Memory Core]
        DB[(Database)]
    end
    
    subgraph "Git Integration"
        PostCommit[Post-Commit Hook]
        PrePush[Pre-Push Hook]
        BranchLink[Branch Linking]
    end
    
    subgraph "CI/CD Integration"
        GHA[GitHub Actions]
        GitLabCI[GitLab CI]
        Jenkins[Jenkins]
    end
    
    subgraph "IDE Integration"
        VSCode[VSCode Extension]
        IntelliJ[IntelliJ Plugin]
    end
    
    subgraph "Team Tools"
        Slack[Slack Notifications]
        Jira[Jira Sync]
        Dashboard[Web Dashboard]
    end
    
    Core --> DB
    
    PostCommit --> Core
    PrePush --> Core
    BranchLink --> Core
    
    GHA --> Core
    GitLabCI --> Core
    Jenkins --> Core
    
    VSCode --> Core
    IntelliJ --> Core
    
    Core --> Slack
    Core --> Jira
    Core --> Dashboard
    
    style Core fill:#f9f,stroke:#333,stroke-width:4px
```

---

## 8. Impact Prediction Process

```mermaid
graph TB
    Start[Changed Files] --> GetHistory[Get File History]
    GetHistory --> FindRelated[Find Related Files]
    
    FindRelated --> CalcConfidence[Calculate Confidence]
    CalcConfidence --> RankFiles[Rank by Confidence]
    
    Start --> FindRisks[Find Historical Risks]
    FindRisks --> MatchPatterns[Match Risk Patterns]
    MatchPatterns --> ScoreRisks[Score Risks]
    
    Start --> FindTasks[Find Similar Tasks]
    FindTasks --> CalcComplexity[Calculate Complexity]
    
    RankFiles --> Output[Prediction Output]
    ScoreRisks --> Output
    CalcComplexity --> Output
    
    Output --> AffectedFiles[Affected Files List]
    Output --> PotentialRisks[Potential Risks]
    Output --> RequiredTests[Required Tests]
    Output --> Complexity[Complexity Estimate]
    
    style Start fill:#bfb
    style Output fill:#bbf
```

---

## 9. Session Timeline Visualization

```mermaid
gantt
    title Session Timeline Example
    dateFormat YYYY-MM-DD
    section Sessions
    Initial Setup           :done, s1, 2026-05-01, 1d
    Auth Implementation     :done, s2, 2026-05-05, 3d
    Security Audit          :done, s3, 2026-05-10, 2d
    Bug Fixes              :done, s4, 2026-05-13, 1d
    Feature Enhancement     :active, s5, 2026-05-15, 2d
    
    section Risks
    SQL Injection          :crit, r1, 2026-05-05, 10d
    Auth Bypass            :crit, r2, 2026-05-08, 7d
    XSS Vulnerability      :r3, 2026-05-10, 5d
    
    section Tasks
    Implement OAuth        :done, t1, 2026-05-05, 5d
    Add Tests             :done, t2, 2026-05-10, 3d
    Update Docs           :active, t3, 2026-05-13, 4d
```

---

## 10. Risk Evolution Tracking

```mermaid
graph LR
    subgraph "Session 1"
        S1_New[New Risk Detected]
    end
    
    subgraph "Session 2"
        S2_Ongoing[Risk Still Present]
        S2_Context[More Context Added]
    end
    
    subgraph "Session 3"
        S3_Ongoing[Risk Persists]
        S3_Severity[Severity Increased]
    end
    
    subgraph "Session 4"
        S4_Resolved[Risk Resolved]
        S4_Solution[Solution Documented]
    end
    
    S1_New --> S2_Ongoing
    S2_Ongoing --> S2_Context
    S2_Context --> S3_Ongoing
    S3_Ongoing --> S3_Severity
    S3_Severity --> S4_Resolved
    S4_Resolved --> S4_Solution
    
    style S1_New fill:#fbb
    style S2_Ongoing fill:#fbb
    style S3_Ongoing fill:#f99
    style S4_Resolved fill:#bfb
```

---

## 11. File Relationship Network

```mermaid
graph TD
    Auth[packages/auth/login.ts]
    OAuth[packages/auth/oauth.ts]
    JWT[packages/auth/jwt.ts]
    Routes[packages/api/routes.ts]
    Tests[tests/auth.test.ts]
    Config[config/auth.config.ts]
    
    Auth -.->|co-change: 0.92| OAuth
    Auth -.->|co-change: 0.87| JWT
    Auth -.->|co-change: 0.78| Tests
    Auth -.->|co-change: 0.65| Routes
    
    OAuth -.->|co-change: 0.85| JWT
    OAuth -.->|co-change: 0.72| Config
    
    JWT -.->|co-change: 0.68| Config
    
    Routes -.->|co-change: 0.55| Tests
    
    style Auth fill:#f9f,stroke:#333,stroke-width:3px
    style OAuth fill:#bbf
    style JWT fill:#bbf
    style Tests fill:#bfb
```

---

## 12. Migration Strategy

```mermaid
graph TB
    subgraph "Phase 1: Dual Mode"
        FileMode[File-Based Mode]
        DBMode[Database Mode]
        Both[Both Supported]
    end
    
    subgraph "Phase 2: Migration"
        Detect[Detect Existing Packs]
        Migrate[Migrate to Database]
        Verify[Verify Migration]
    end
    
    subgraph "Phase 3: Transition"
        Default[Database Default]
        FileOptional[File Mode Optional]
        Deprecate[Deprecate File-Only]
    end
    
    subgraph "Phase 4: Full Database"
        DBOnly[Database Only]
        Export[Export to Files]
        Backward[Backward Compat]
    end
    
    FileMode --> Both
    DBMode --> Both
    Both --> Detect
    
    Detect --> Migrate
    Migrate --> Verify
    Verify --> Default
    
    Default --> FileOptional
    FileOptional --> Deprecate
    Deprecate --> DBOnly
    
    DBOnly --> Export
    DBOnly --> Backward
    
    style Both fill:#bbf
    style Verify fill:#bfb
    style DBOnly fill:#f9f
```

---

## 13. Performance Optimization Strategy

```mermaid
graph TB
    subgraph "Data Layer"
        Indexes[Strategic Indexes]
        Views[Materialized Views]
        Partitions[Table Partitioning]
    end
    
    subgraph "Query Layer"
        Cache[Query Cache]
        Prepared[Prepared Statements]
        Batch[Batch Operations]
    end
    
    subgraph "Application Layer"
        Lazy[Lazy Loading]
        Pagination[Result Pagination]
        Async[Async Processing]
    end
    
    subgraph "Storage Layer"
        Compression[Data Compression]
        Archive[Old Data Archive]
        Vacuum[Regular Vacuum]
    end
    
    Indexes --> Cache
    Views --> Cache
    Partitions --> Cache
    
    Cache --> Lazy
    Prepared --> Lazy
    Batch --> Lazy
    
    Lazy --> Compression
    Pagination --> Archive
    Async --> Vacuum
    
    style Cache fill:#bbf
    style Archive fill:#fbb
```

---

## Summary

These diagrams illustrate the complete Multi-Session Memory System architecture:

1. **System Architecture**: Overall component structure
2. **Database Schema**: Entity relationships and data model
3. **Data Flow**: How sessions are recorded
4. **Query Processing**: How queries are executed
5. **Intelligence Engine**: Pattern detection and prediction
6. **Team Collaboration**: Multi-user workflows
7. **Integration Points**: External system connections
8. **Impact Prediction**: Prediction algorithm flow
9. **Session Timeline**: Temporal visualization
10. **Risk Evolution**: How risks are tracked over time
11. **File Relationships**: Co-change network
12. **Migration Strategy**: Transition from file-based to database
13. **Performance**: Optimization strategies

These diagrams can be rendered in any Mermaid-compatible viewer or documentation system.