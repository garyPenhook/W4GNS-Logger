"""
SQLAlchemy ORM Models for W4GNS SKCC Logger Database

Defines all database models for contacts, QSL records, awards, and cluster spots.
"""

from datetime import datetime, timezone
from sqlalchemy import (
    Column, Integer, String, Float, Text, DateTime,
    ForeignKey, UniqueConstraint, Index, create_engine
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class Contact(Base):
    """
    Contact/QSO Record - Supports all ADIF 3.1.5 fields with configurable GUI display.

    IMPORTANT: All times and dates MUST be in UTC format for consistent logging across timezones.
    - qso_date: UTC date in YYYYMMDD format (ADIF standard)
    - time_on: UTC time in HHMM format (ADIF standard)
    - time_off: UTC time in HHMM format (ADIF standard)
    - qsl_sent_date: UTC date in YYYYMMDD format
    - qsl_rcvd_date: UTC date in YYYYMMDD format
    """

    __tablename__ = "contacts"

    id = Column(Integer, primary_key=True)

    # === BASIC FIELDS (Always displayed in GUI by default) ===
    callsign = Column(String(12), nullable=False, index=True)
    qso_date = Column(String(8), nullable=False, index=True)  # YYYYMMDD (UTC)
    time_on = Column(String(4), nullable=False)  # HHMM (UTC)
    band = Column(String(10), nullable=False, index=True)  # 160M, 80M, etc.
    mode = Column(String(20), nullable=False, index=True, default="CW")  # CW, SSB, FM, etc. (default: CW)

    # === EXTENDED QSO FIELDS ===
    time_off = Column(String(4))  # HHMM (UTC)
    frequency: Column[float] = Column(Float)  # type: ignore[assignment]  # MHz
    freq_rx: Column[float] = Column(Float)  # type: ignore[assignment]  # RX frequency
    rst_sent = Column(String(3))  # Signal report sent
    rst_rcvd = Column(String(3))  # Signal report received
    tx_power: Column[float] = Column(Float)  # type: ignore[assignment]  # Watts
    rx_power: Column[float] = Column(Float)  # type: ignore[assignment]  # Watts

    # === GRID/LOCATION FIELDS ===
    my_gridsquare = Column(String(10))  # My grid square
    gridsquare = Column(String(10))  # Remote grid square
    my_city = Column(String(100))
    my_country = Column(String(100))
    my_state = Column(String(2))
    name = Column(String(100))  # Remote operator name
    qth = Column(String(100))  # Remote location
    country = Column(String(100), index=True)

    # === GEOGRAPHIC/AWARD FIELDS ===
    dxcc = Column(Integer, index=True)  # DXCC entity
    cqz = Column(Integer)  # CQ Zone
    ituz = Column(Integer)  # ITU Zone
    state = Column(String(2), index=True)  # US state
    county = Column(String(100))
    arrl_sect = Column(String(3))  # ARRL section
    iota = Column(String(10))  # Islands on Air
    iota_island_id = Column(String(10))
    sota_ref = Column(String(20))  # Summits on Air
    pota_ref = Column(String(20))  # Parks on Air
    vucc_grids = Column(String(100))  # VUCC grids

    # === STATION/EQUIPMENT FIELDS ===
    operator = Column(String(100))
    station_callsign = Column(String(12))
    my_rig = Column(String(100))
    my_rig_make = Column(String(50))  # My rig manufacturer (e.g., Yaesu, Kenwood, ICOM)
    my_rig_model = Column(String(50))  # My rig model number
    rig_make = Column(String(50))
    rig_model = Column(String(50))
    my_antenna = Column(String(100))
    my_antenna_make = Column(String(50))  # My antenna manufacturer
    my_antenna_model = Column(String(50))  # My antenna model
    antenna_make = Column(String(50))
    antenna_model = Column(String(50))

    # === AWARD/CLUB FIELDS ===
    skcc_number = Column(String(20))  # Straight Key Century Club member number
    key_type = Column(String(20), default="STRAIGHT")  # Key type: STRAIGHT, BUG, SIDESWIPER
    paddle = Column(String(20))  # Paddle type: ELECTRONIC, SEMI-AUTO, IAMBIC, MECHANICAL (not valid for SKCC)

    # === PROPAGATION/TECHNICAL FIELDS ===
    propagation_mode = Column(String(30))  # Satellite, EME, etc.
    sat_name = Column(String(50))
    sat_mode = Column(String(20))
    a_index = Column(Integer)  # Solar A-Index
    k_index = Column(Integer)  # Solar K-Index
    sfi = Column(Integer)  # Solar Flux Index
    antenna_az: Column[float] = Column(Float)  # type: ignore[assignment]  # Azimuth
    antenna_el: Column[float] = Column(Float)  # type: ignore[assignment]  # Elevation
    distance: Column[float] = Column(Float)  # type: ignore[assignment]  # km
    latitude: Column[float] = Column(Float)  # type: ignore[assignment]
    longitude: Column[float] = Column(Float)  # type: ignore[assignment]

    # === QSL/CONFIRMATION FIELDS ===
    qsl_rcvd = Column(String(1))  # Y/N/V
    qsl_sent = Column(String(1))  # Y/N/V
    qsl_rcvd_date = Column(String(8))  # YYYYMMDD (UTC)
    qsl_sent_date = Column(String(8))  # YYYYMMDD (UTC)
    qsl_via = Column(String(50))  # DIRECT, BUREAU, MANAGER
    lotw_qsl_rcvd = Column(String(1))  # Y/N
    lotw_qsl_sent = Column(String(1))  # Y/N
    eqsl_qsl_rcvd = Column(String(1))  # Y/N
    eqsl_qsl_sent = Column(String(1))  # Y/N
    clublog_status = Column(String(30))

    # === NOTES/COMMENTS ===
    notes = Column(Text)
    comment = Column(Text)
    qslmsg = Column(Text)

    # === CONTEST/AWARD FIELDS ===
    contest_id = Column(String(50))
    class_field = Column(String(30))  # Contest class
    check = Column(String(10))  # Contest check

    # === METADATA ===
    qrz_uploaded = Column(Integer, default=0)
    qrz_upload_date = Column(String(8))
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    qsl_records = relationship("QSLRecord", back_populates="contact")

    __table_args__ = (
        UniqueConstraint("callsign", "qso_date", "time_on", "band", name="unique_qso"),
        # Composite indexes for frequently used query patterns
        Index("idx_callsign_qso_date_band", "callsign", "qso_date", "band"),
        Index("idx_band_mode_qso_date", "band", "mode", "qso_date"),
        Index("idx_country_dxcc_state", "country", "dxcc", "state"),
        Index("idx_qso_date_band_mode", "qso_date", "band", "mode"),
        Index("idx_band_mode_country", "band", "mode", "country"),
        Index("idx_callsign_band_mode", "callsign", "band", "mode"),
        Index("idx_qso_date_country", "qso_date", "country"),
        Index("idx_state_country_dxcc", "state", "country", "dxcc"),
        # SKCC award indexes
        Index("idx_skcc_number", "skcc_number"),
        Index("idx_skcc_callsign_band_mode", "skcc_number", "callsign", "band", "mode"),
        # Key type indexes
        Index("idx_key_type", "key_type"),
        Index("idx_key_type_band_mode", "key_type", "band", "mode"),
        Index("idx_skcc_key_type", "skcc_number", "key_type"),
    )

    def validate_skcc(self) -> None:
        """Validate that SKCC contacts are CW-only, use mechanical keys only, and cannot use paddles"""
        if self.skcc_number:
            if self.mode and self.mode.upper() != "CW":
                raise ValueError(f"SKCC contacts must be CW mode only. Got mode: {self.mode}")
            if self.paddle:
                raise ValueError(f"SKCC contacts cannot use paddles. Got paddle: {self.paddle}")
            if self.key_type and self.key_type.upper() not in ["STRAIGHT", "BUG", "SIDESWIPER"]:
                raise ValueError(f"SKCC contacts must use mechanical keys only (STRAIGHT, BUG, SIDESWIPER). Got: {self.key_type}")

    # === QRP POWER TRACKING METHODS ===

    def is_qrp_contact(self) -> bool:
        """
        Check if contact qualifies as QRP (5W or less)

        Returns:
            True if tx_power is ≤5W, False otherwise
        """
        return self.tx_power is not None and self.tx_power <= 5.0

    def is_qrp_two_way(self, other_station_power: float) -> bool:
        """
        Check if both stations are QRP (5W or less)

        Args:
            other_station_power: Power of the other station (in watts)

        Returns:
            True if both stations at ≤5W, False otherwise
        """
        return (self.tx_power is not None and self.tx_power <= 5.0 and
                other_station_power is not None and other_station_power <= 5.0)

    def calculate_mpw(self, distance_miles: float) -> float:
        """
        Calculate Miles Per Watt ratio for QRP MPW award

        Args:
            distance_miles: Distance to contacted station in miles

        Returns:
            Miles Per Watt ratio (distance / power)
        """
        if self.tx_power is None or self.tx_power <= 0:
            return 0
        return distance_miles / self.tx_power

    def qualifies_for_mpw(self, distance_miles: float) -> bool:
        """
        Check if QSO qualifies for MPW award (≥1000 MPW at ≤5W)

        Args:
            distance_miles: Distance to contacted station in miles

        Returns:
            True if qualifies for MPW award, False otherwise
        """
        return (self.tx_power is not None and self.tx_power <= 5.0 and
                self.calculate_mpw(distance_miles) >= 1000.0)

    def get_qrp_category(self) -> str:
        """
        Categorize contact by transmit power level

        Returns:
            Category: 'QRPp' (<0.5W), 'QRP' (0.5-5W), 'STANDARD' (5-100W), 'QRO' (>100W)
        """
        if self.tx_power is None:
            return "UNKNOWN"
        if self.tx_power < 0.5:
            return "QRPp"
        elif self.tx_power <= 5.0:
            return "QRP"
        elif self.tx_power <= 100.0:
            return "STANDARD"
        else:
            return "QRO"

    def __repr__(self) -> str:
        return f"<Contact(callsign={self.callsign}, date={self.qso_date}, band={self.band})>"


class QSLRecord(Base):
    """QSL Confirmation Record"""

    __tablename__ = "qsl_records"

    id = Column(Integer, primary_key=True)
    contact_id = Column(Integer, ForeignKey("contacts.id"), nullable=False, index=True)
    confirmation_type = Column(String(20), nullable=False)  # QSL, LOTW, EQSL, CLUB
    confirmed_date = Column(String(8))  # YYYYMMDD
    confirmation_source = Column(String(50))  # Authority (ARRL, LoTW, etc.)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    contact = relationship("Contact", back_populates="qsl_records")

    __table_args__ = (
        # Composite indexes for QSL record queries
        Index("idx_contact_confirmation_type", "contact_id", "confirmation_type"),
        Index("idx_confirmation_type_date", "confirmation_type", "confirmed_date"),
    )

    def __repr__(self) -> str:
        return f"<QSLRecord(contact_id={self.contact_id}, type={self.confirmation_type})>"


class AwardProgress(Base):
    """Award Program Progress Tracking"""

    __tablename__ = "awards_progress"

    id = Column(Integer, primary_key=True)
    award_program = Column(String(50), nullable=False, index=True)  # DXCC, WAS, etc.
    award_name = Column(String(100), nullable=False)
    award_mode = Column(String(20))  # MIXED, CW, PHONE, DIGITAL
    award_band = Column(String(10))  # Specific band or NULL for all-band

    # Progress
    contact_count = Column(Integer, default=0)
    entity_count = Column(Integer, default=0)
    points_total = Column(Integer, default=0)

    # Status
    achievement_level = Column(String(50))
    achieved_date = Column(String(8))  # YYYYMMDD
    last_updated = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    notes = Column(Text)

    __table_args__ = (
        UniqueConstraint(
            "award_program", "award_name", "award_mode", "award_band",
            name="unique_award"
        ),
        # Composite indexes for award tracking queries
        Index("idx_award_program_name", "award_program", "award_name"),
        Index("idx_award_mode_band", "award_mode", "award_band"),
        Index("idx_award_program_mode_band", "award_program", "award_mode", "award_band"),
    )

    def __repr__(self) -> str:
        return f"<AwardProgress(program={self.award_program}, name={self.award_name})>"


class ClusterSpot(Base):
    """DX Cluster Spot Record (Optional persistent storage)"""

    __tablename__ = "cluster_spots"

    id = Column(Integer, primary_key=True)
    frequency: Column[float] = Column(Float, nullable=False)  # type: ignore[assignment]
    dx_callsign = Column(String(12), nullable=False, index=True)
    de_callsign = Column(String(12))  # Spotting station
    dx_grid = Column(String(10))  # Grid square if available
    comment = Column(Text)

    received_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    spotted_date = Column(String(8))  # YYYYMMDD
    spotted_time = Column(String(4))  # HHMM

    __table_args__ = (
        # Composite indexes for cluster spot queries
        Index("idx_spotted_date_time", "spotted_date", "spotted_time"),
        Index("idx_dx_callsign_frequency", "dx_callsign", "frequency"),
        Index("idx_spotted_date_frequency", "spotted_date", "frequency"),
    )


class CenturionMember(Base):
    """SKCC Centurion Award Member List - Updated Daily from SKCC"""

    __tablename__ = "centurion_members"

    id = Column(Integer, primary_key=True)
    rank = Column(Integer, nullable=False, index=True)  # Ranking number (1-based)
    callsign = Column(String(12), nullable=False, unique=True, index=True)  # Callsign
    skcc_number = Column(String(20), nullable=False, index=True)  # SKCC member number
    name = Column(String(100))  # Operator name
    city = Column(String(100))
    state = Column(String(2))
    country = Column(String(50))
    centurion_date = Column(String(8))  # Date achieved YYYYMMDD
    endorsements = Column(String(500))  # Multi-band/single-band endorsement details

    # Metadata
    last_list_update = Column(DateTime, default=lambda: datetime.now(timezone.utc))  # When this list was fetched

    __table_args__ = (
        Index("idx_skcc_number_centurion", "skcc_number"),
        Index("idx_callsign_centurion", "callsign"),
        Index("idx_centurion_date", "centurion_date"),
    )

    def __repr__(self) -> str:
        return f"<CenturionMember(rank={self.rank}, call={self.callsign}, skcc={self.skcc_number})>"


class TribuneeMember(Base):
    """SKCC Tribune Award Member List - Updated Daily from SKCC"""

    __tablename__ = "tribune_members"

    id = Column(Integer, primary_key=True)
    rank = Column(Integer, nullable=False, index=True)  # Ranking number (1-based)
    callsign = Column(String(12), nullable=False, unique=True, index=True)  # Callsign
    skcc_number = Column(String(20), nullable=False, index=True)  # SKCC member number
    name = Column(String(100))  # Operator name
    city = Column(String(100))
    state = Column(String(2))
    country = Column(String(50))
    tribune_date = Column(String(8))  # Date achieved YYYYMMDD
    endorsements = Column(String(500))  # Multi-band/single-band endorsement details

    # Metadata
    last_list_update = Column(DateTime, default=lambda: datetime.now(timezone.utc))  # When this list was fetched

    __table_args__ = (
        Index("idx_skcc_number_tribune", "skcc_number"),
        Index("idx_callsign_tribune", "callsign"),
        Index("idx_tribune_date", "tribune_date"),
    )

    def __repr__(self) -> str:
        return f"<TribuneeMember(rank={self.rank}, call={self.callsign}, skcc={self.skcc_number})>"


class SenatorMember(Base):
    """SKCC Senator Award Member List - Updated Daily from SKCC"""

    __tablename__ = "senator_members"

    id = Column(Integer, primary_key=True)
    rank = Column(Integer, nullable=False, index=True)  # Ranking number (1-based)
    callsign = Column(String(12), nullable=False, unique=True, index=True)  # Callsign
    skcc_number = Column(String(20), nullable=False, index=True)  # SKCC member number
    name = Column(String(100))  # Operator name
    city = Column(String(100))
    state = Column(String(2))
    country = Column(String(50))
    senator_date = Column(String(8))  # Date achieved YYYYMMDD
    endorsements = Column(String(500))  # Multi-band/single-band endorsement details

    # Metadata
    last_list_update = Column(DateTime, default=lambda: datetime.now(timezone.utc))  # When this list was fetched

    __table_args__ = (
        Index("idx_skcc_number_senator", "skcc_number"),
        Index("idx_callsign_senator", "callsign"),
        Index("idx_senator_date", "senator_date"),
    )

    def __repr__(self) -> str:
        return f"<SenatorMember(rank={self.rank}, call={self.callsign}, skcc={self.skcc_number})>"


class Configuration(Base):
    """Application Configuration Storage"""

    __tablename__ = "configuration"

    id = Column(Integer, primary_key=True)
    key = Column(String(100), unique=True, nullable=False)
    value = Column(Text)
    value_type = Column(String(20))  # string, integer, boolean, json
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    def __repr__(self) -> str:
        return f"<Configuration(key={self.key}, value={self.value})>"


class UIFieldPreference(Base):
    """User's field display preferences in GUI

    Allows users to toggle which fields are visible in contact forms and lists.
    Basic fields are always shown. Extended fields shown based on these preferences.
    """

    __tablename__ = "ui_field_preferences"

    id = Column(Integer, primary_key=True)
    field_name = Column(String(100), unique=True, nullable=False)
    display_in_list = Column(Integer, default=0)  # Boolean: show in contacts list
    display_in_form = Column(Integer, default=0)  # Boolean: show in contact form
    column_position = Column(Integer, default=999)  # Order in list/form
    display_name = Column(String(100))  # Human-readable field name
    field_category = Column(String(50))  # QSO, Location, QSL, Technical, etc.
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        # Composite index for field preference queries
        Index("idx_display_in_list_position", "display_in_list", "column_position"),
        Index("idx_field_category", "field_category"),
    )

    def __repr__(self) -> str:
        return f"<UIFieldPreference(field={self.field_name}, list={self.display_in_list}, form={self.display_in_form})>"


def create_database(db_path: str) -> None:
    """
    Create database and tables

    Args:
        db_path: Path to SQLite database file
    """
    engine = create_engine(f"sqlite:///{db_path}", echo=False)
    Base.metadata.create_all(engine)
    print(f"Database created at: {db_path}")
