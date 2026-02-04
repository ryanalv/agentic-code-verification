# Task: Refactor to Hexagonal Architecture

## Goal
Restructure the project into a Hexagonal Architecture (Ports and Adapters) to decouple business logic from dependencies like PraisonAI and File System.

## Checklist

### 1. Planning & Design
- [ ] Define Domain Entities (ReviewResult, Section).
- [ ] Define Ports (Input/Output Interfaces).
- [ ] Map existing components to the new structure.

### 2. Core (Domain & Application)
- [ ] Create `src/core/domain/` and define data models.
- [ ] Create `src/core/ports/` and define abstract base classes (`ICritic`).
- [ ] Create `src/core/use_cases/` and implement `PerformReviewUseCase` (formerly ReviewPipeline).

### 3. Adapters (Infrastructure)
- [ ] Create `src/infrastructure/adapters/praison_critic.py` (Implementation of ICritic).
- [ ] Create `src/infrastructure/adapters/file_system.py` (File operations).
- [ ] Move `text_splitter.py` to `infrastructure/utils`.

### 4. Wiring & Entry Points
- [ ] Create Dependency Injection container or factory (`src/main/factory.py`).
- [ ] Update `tests` to verify the new structure.
- [ ] Update `walkthrough.md` to explain the new architecture.
