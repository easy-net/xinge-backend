from sqlalchemy import Boolean, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class School(Base):
    __tablename__ = "schools"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    city: Mapped[str] = mapped_column(String(128), nullable=False)
    city_level: Mapped[str] = mapped_column(String(64), nullable=False)
    is_985: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_211: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_double_first_class: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    school_level_tag: Mapped[str] = mapped_column(String(128), default="", nullable=False)
    school_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    colleges = relationship("College", back_populates="school", cascade="all, delete-orphan")


class College(Base):
    __tablename__ = "colleges"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    school_id: Mapped[int] = mapped_column(ForeignKey("schools.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    college_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    school = relationship("School", back_populates="colleges")
    majors = relationship("Major", back_populates="college", cascade="all, delete-orphan")


class Major(Base):
    __tablename__ = "majors"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    college_id: Mapped[int] = mapped_column(ForeignKey("colleges.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    major_type: Mapped[str] = mapped_column(String(128), default="", nullable=False)
    major_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    college = relationship("College", back_populates="majors")

