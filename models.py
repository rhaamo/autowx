from sqlalchemy import create_engine, Column, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

Base = declarative_base()


def init(config):
    """
    Returns the engine after creating all tables if needed.
    """
    engine = create_engine(config.get('DB', 'path'), echo=False)
    Base.metadata.create_all(engine)
    return engine


def get_session(engine):
    return sessionmaker(bind=engine)


class Passes(Base):
    __tablename__ = 'passes'

    id = Column(Integer, primary_key=True)

    sat_name = Column(String, nullable=False)
    automate_started = Column(DateTime, nullable=False)
    aos_time = Column(DateTime, nullable=False)
    los_time = Column(DateTime, nullable=False)
    max_elev = Column(Integer, nullable=False)
    record_time = Column(Integer, nullable=False)
    sat_type = Column(String, nullable=True)

    def __repr__(self):
        return "<Passes(id='%i', sat='%s', aos='%s', los='%s', max_elev='%i')>".format(
            self.id, self.sat_name, self.aos_time, self.los_time, self.max_elev
        )
