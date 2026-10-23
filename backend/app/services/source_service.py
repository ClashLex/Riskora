from app.domain.models import Holding, SourceRecord


def sources_for_ids(
    sources: list[SourceRecord],
    holdings: list[Holding],
    source_ids: set[str],
) -> list[dict]:
    records = {
        source.id: source.model_dump(mode="json") for source in sources if source.id in source_ids
    }
    for holding in holdings:
        if holding.source_id in source_ids and holding.source_id not in records:
            records[holding.source_id] = {
                "id": holding.source_id,
                "name": holding.source_label,
                "source_url": holding.source_url,
                "as_of_date": holding.as_of_date.isoformat(),
                "retrieved_at": None,
                "data_status": holding.data_status.value,
                "license_note": "User-provided source metadata; not independently verified.",
                "fields_supported": ["holding identity", "market value", "currency"],
            }
    return [records[source_id] for source_id in sorted(records)]
