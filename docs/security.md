# Security and Privacy

## 1. Purpose

FraudLens handles financial-style transaction data and therefore follows conservative data-handling practices even though the project is based on public or generated data.

---

## 2. Sensitive Information

Never commit:

* passwords;
* API keys;
* database credentials;
* private tokens;
* real payment information;
* unnecessary personal information.

---

## 3. Dataset Safety

The project should use:

* public datasets;
* appropriately licensed datasets;
* synthetic data.

Real personal financial information must not be introduced into the repository.

---

## 4. Secrets

Secrets belong in environment variables or an appropriate secret-management system.

Never place secrets in:

* source code;
* README files;
* notebooks;
* configuration committed to Git;
* screenshots.

---

## 5. API Security

The API must not expose:

* credentials;
* internal paths;
* database connection strings;
* secret configuration;
* unnecessary model internals.

---

## 6. Logging

Logs should avoid sensitive transaction details.

Prefer:

```text
transaction_id
model_version
timestamp
status
```

over unnecessary sensitive payload logging.

---

## 7. Data Minimization

Only retain fields necessary for the project's analytical objectives.

---

## 8. Portfolio Safety

All examples shown publicly should be safe for public release.

No real customer information should appear in:

* GitHub;
* screenshots;
* Power BI dashboards;
* API examples;
* README files.
