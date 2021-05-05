def row2dict(row):
    """Convert SQLAlchemy row to dict."""
    d = {}
    for column in row.__table__.columns:
        d[column.name] = getattr(row, column.name)
    return d
