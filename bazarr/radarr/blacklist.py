# coding=utf-8

from datetime import datetime

from app.database import TableBlacklistMovie, database, insert, delete
from app.event_handler import event_stream


def get_blacklist_movie():
    return [(item.provider, item.subs_id) for item in
            database.query(TableBlacklistMovie.provider, TableBlacklistMovie.subs_id).all()]


def blacklist_log_movie(radarr_id, provider, subs_id, language):
    database.execute(insert(TableBlacklistMovie).values(
        radarr_id=radarr_id,
        timestamp=datetime.now(),
        provider=provider,
        subs_id=subs_id,
        language=language
    ))
    database.commit()
    event_stream(type='movie-blacklist')


def blacklist_delete_movie(provider, subs_id):
    database.execute(delete(TableBlacklistMovie)
                     .where((TableBlacklistMovie.provider == provider) and
                            (TableBlacklistMovie.subs_id == subs_id)))
    database.commit()
    event_stream(type='movie-blacklist', action='delete')


def blacklist_delete_all_movie():
    database.execute(delete(TableBlacklistMovie))
    database.commit()
    event_stream(type='movie-blacklist', action='delete')
