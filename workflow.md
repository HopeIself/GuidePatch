# Workflow

```mermaid
flowchart TD
 A[Old tutorial + current UI + goal] --> B[Normalize environment and intent]
 B --> C[Observe and classify each step]
 C --> D{Evidence adequate and low risk?}
 D -->|No| E[BLOCKED: ask for evidence]
 D -->|Yes| F[Keep unaffected steps or build minimal replacement]
 F --> G[Validate structured case]
 G --> H[Show next action and expected state]
 H --> I{Explicit feedback}
 I -->|Failed| J[Stop at failing step and rebuild]
 I -->|Successful| K[Record action and environment]
 K --> L{All steps and final goal confirmed?}
 L -->|No| H
 L -->|Yes| M[Export verified patch; local reuse with consent]
 E --> B
 J --> B
```

Unknown version/language/context: ask, mark blocked until exact scope known. Blurry/partial screenshot: request relevant crop/transcription. Conflicting evidence: describe conflict, no execution candidate. Risky action: pause and refer to appropriate official guidance. Failure: never try random alternate paths, revise with new evidence; old revision feedback cannot be replayed. A simulation can test the mechanics but can never produce a real VERIFIED record.

## 处理用户更正

用户纠正页面标题时，记录更正后的可见内容，再确认目标。找下载记录时，以下载条目或空列表提示为准。
