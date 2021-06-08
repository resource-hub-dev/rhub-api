def row2dict(row):
    """Convert SQLAlchemy row to dict."""
    if hasattr(row, 'to_dict'):
        return row.to_dict()
    d = {}
    for column in row.__table__.columns:
        d[column.name] = getattr(row, column.name)
    return d
