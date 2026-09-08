# Deployment

## 1. Current Target

The initial MVP is intended to run locally.

Cloud deployment is a later phase.

---

## 2. Local Architecture

```text
Developer Machine
      |
      +-- PostgreSQL
      |
      +-- dbt
      |
      +-- ML Pipeline
      |
      +-- FastAPI
```

---

## 3. Docker

Docker may eventually package:

```text
API
Database
Supporting services
```

The Docker architecture should only be introduced once the local application is stable.

---

## 4. CI/CD

GitHub Actions may eventually automate:

```text
lint
tests
type checking
dbt tests
build
```

Deployment automation should only be added after CI is reliable.

---

## 5. Cloud

Potential future architecture:

```text
                    AWS
                     |
       +-------------+-------------+
       |                           |
   Application                 Database
       |                           |
    FastAPI                   PostgreSQL
       |
    Risk Model
```

Potential technologies:

* AWS;
* Terraform;
* managed PostgreSQL;
* container hosting.

---

## 6. Deployment Principle

Do not introduce cloud infrastructure simply to make the architecture look impressive.

Every infrastructure component must solve a real problem.
