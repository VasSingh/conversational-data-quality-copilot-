"""Generate synthetic enterprise data if not present.
Creates entities.csv, dq_exceptions.csv, remediation.csv in the data/ folder.
"""
import os
from datetime import datetime, timedelta
import random
from typing import List

import numpy as np
import pandas as pd
from faker import Faker

fake = Faker()


def _generate_entities(n: int = 10000) -> pd.DataFrame:
    countries = ["Germany", "France", "Switzerland", "United Kingdom", "India", "United States", "Singapore", "Japan"]
    industries = ["Banking", "Insurance", "Asset Management", "Technology", "Manufacturing"]

    rows = []
    for i in range(1, n + 1):
        rows.append({
            "entity_id": i,
            "legal_name": fake.company(),
            "country": random.choice(countries),
            "industry": random.choice(industries),
            "incorporation_date": fake.date_between(start_date='-30y', end_date='today'),
            "source_system": random.choice(["ERP", "CRM", "RegSys", "PartnerFeed"]),
            "risk_rating": random.choice(["Low", "Medium", "High"]),
        })

    return pd.DataFrame(rows)


def _generate_exceptions(n: int = 100000, num_entities: int = 10000) -> pd.DataFrame:
    rules = ["Country Mismatch", "Missing Parent Entity", "Invalid Registration Number", "Missing Tax Identifier", "Hierarchy Conflict", "Duplicate Entity"]
    severities = ["Low", "Medium", "High", "Critical"]

    start = datetime.now() - timedelta(days=730)
    rows = []
    for i in range(1, n + 1):
        entity = random.randint(1, num_entities)
        # Bias patterns
        country = random.choice(["Germany"] * 8 + ["France", "Switzerland", "United Kingdom", "India", "United States", "Singapore", "Japan"])
        rule = random.choice(rules)

        # Increase Switzerland hierarchy conflicts
        if random.random() < 0.02:
            country = "Switzerland"
            rule = "Hierarchy Conflict"

        # Increase Germany country mismatch
        if random.random() < 0.05:
            country = "Germany"
            rule = "Country Mismatch"

        rows.append({
            "exception_id": i,
            "entity_id": entity,
            "rule_name": rule,
            "severity": random.choices(severities, weights=[60,25,10,5])[0],
            "country": country,
            "exception_date": (start + timedelta(days=random.randint(0, 730))).date(),
            "status": random.choices(["open", "in_progress", "resolved"], weights=[30,20,50])[0],
        })

    return pd.DataFrame(rows)


def _generate_remediation(entities_df: pd.DataFrame, exceptions_df: pd.DataFrame) -> pd.DataFrame:
    owners = ["Data Stewards", "Data Ops", "Platform Team", "Business Analysts"]
    rows = []
    # Map some entities to remediation records
    entity_ids = entities_df['entity_id'].sample(frac=0.3, replace=False).tolist()
    for eid in entity_ids:
        res_days = int(np.abs(np.random.normal(loc=5, scale=4)))
        rows.append({
            "entity_id": int(eid),
            "resolution_days": res_days,
            "owner_team": random.choice(owners),
            "status": random.choice(["open", "closed"]),
            "sla_target": random.choice([3,5,7,14])
        })

    return pd.DataFrame(rows)


def ensure_data(data_dir: str = "data") -> None:
    os.makedirs(data_dir, exist_ok=True)
    ent_path = os.path.join(data_dir, "entities.csv")
    exc_path = os.path.join(data_dir, "dq_exceptions.csv")
    rem_path = os.path.join(data_dir, "remediation.csv")

    if not os.path.exists(ent_path) or not os.path.exists(exc_path) or not os.path.exists(rem_path):
        # Generate datasets
        entities = _generate_entities(10000)
        exceptions = _generate_exceptions(100000, num_entities=10000)
        remediation = _generate_remediation(entities, exceptions)

        # Save CSVs
        entities.to_csv(ent_path, index=False)
        exceptions.to_csv(exc_path, index=False)
        remediation.to_csv(rem_path, index=False)
