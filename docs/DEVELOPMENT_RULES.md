# Development Rules

General

- Follow the numerical method defined in `paper/`
- Implementation must be inside `src/`
- Tests must be added for new functionality

Coding Rules

- No global mutable state
- Dependencies via constructor injection
- Backend must use `xp = backend.xp`
- Support `ndim = 2 or 3`

Testing

Every new feature must include:

- unit test
- numerical validation when possible

Prohibited

- referencing deleted directories
- hardcoding numpy when backend exists
- adding external dependencies without reason