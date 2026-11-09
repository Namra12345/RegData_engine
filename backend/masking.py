# PII masking utilities
def mask_sensitive_data(record: dict, role: str) -> dict:
    """
    Masks PII fields if the user's role is not 'compliance_officer'.
    Sensitive fields: customer_name, kyc_id, account_id, counterparty_account_id.
    """
    # Compliance officers see everything unmasked
    if role == "compliance_officer":
        return record

    masked_record = record.copy()

    # Mask account_id (e.g., ACC-1234 -> ACC-XXXX)
    if "account_id" in masked_record and masked_record["account_id"]:
        acc = str(masked_record["account_id"])
        if len(acc) > 4:
            masked_record["account_id"] = acc[:-4] + "XXXX"
        else:
            masked_record["account_id"] = "XXXX"

    # Mask counterparty_account_id
    if "counterparty_account_id" in masked_record and masked_record["counterparty_account_id"]:
        c_acc = str(masked_record["counterparty_account_id"])
        if len(c_acc) > 4:
            masked_record["counterparty_account_id"] = c_acc[:-4] + "XXXX"
        else:
            masked_record["counterparty_account_id"] = "XXXX"

    # Mask customer_name (e.g., John Smith -> JXXXX SXXXX)
    if "customer_name" in masked_record and masked_record["customer_name"]:
        name_parts = str(masked_record["customer_name"]).split()
        masked_parts = []
        for part in name_parts:
            if len(part) > 1:
                masked_parts.append(part[0] + "X" * (len(part) - 1))
            else:
                masked_parts.append("X")
        masked_record["customer_name"] = " ".join(masked_parts)

    # Mask kyc_id (e.g., Aadhar/Passport number -> XXXXXX229Z)
    if "kyc_id" in masked_record and masked_record["kyc_id"]:
        kyc = str(masked_record["kyc_id"])
        if len(kyc) > 6:
            masked_record["kyc_id"] = "X" * 6 + kyc[6:]
        else:
            masked_record["kyc_id"] = "XXXXXXXX"

    return masked_record