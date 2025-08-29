from sqlalchemy import Column, String, Boolean, Text, Integer, Date, Numeric, DateTime
from sqlalchemy.orm import relationship
from app.models.base import BaseModel
from datetime import datetime, date, timedelta


class LearningCenter(BaseModel):
    __tablename__ = "learning_centers"

    # Basic info
    name = Column(String(100), nullable=False)
    description = Column(Text)

    # Contact info
    main_phone = Column(String(20))
    website = Column(String(200))

    # Settings
    is_active = Column(Boolean, default=False, nullable=False)  # Default False until first payment

    # Branding
    logo_url = Column(String(500))

    # Registration phone (for login)
    registration_number = Column(String(50))

    # Limits
    max_branches = Column(Integer, default=5)
    max_students = Column(Integer, default=1000)

    # Payment & Subscription Management
    remaining_days = Column(Integer, default=0, nullable=False)  # Days of service left
    expires_at = Column(Date)  # When service expires (calculated from remaining_days)
    last_payment_date = Column(Date)  # Last payment received
    total_paid = Column(Numeric(10, 2), default=0.00)  # Lifetime payment amount

    # Relationships
    users = relationship("User", back_populates="learning_center", cascade="all, delete-orphan")
    courses = relationship("Course", back_populates="learning_center", cascade="all, delete-orphan")
    branches = relationship("Branch", back_populates="learning_center", cascade="all, delete-orphan")
    daily_leaderboards = relationship("DailyLeaderboard", back_populates="learning_center",
                                      cascade="all, delete-orphan")
    payments = relationship("Payment", back_populates="learning_center", cascade="all, delete-orphan")

    def __str__(self):
        return f"LearningCenter({self.name}, {self.remaining_days} days left)"

    @property
    def total_users(self):
        return len(self.users)

    @property
    def active_users(self):
        return len([u for u in self.users if u.is_active])

    @property
    def total_courses(self):
        return len(self.courses)

    @property
    def active_courses(self):
        return len([c for c in self.courses if c.is_active])

    @property
    def total_branches(self):
        return len(self.branches)

    @property
    def active_branches(self):
        return len([b for b in self.branches if b.is_active])

    @property
    def total_payments(self):
        return len(self.payments)

    @property
    def account_status(self):
        """Get account status based on remaining days"""
        if self.remaining_days <= 0:
            return "expired"
        elif self.remaining_days <= 7:
            return "expiring_soon"
        elif self.remaining_days <= 30:
            return "active_warning"
        else:
            return "active"

    @property
    def days_until_expiration(self):
        """Get days until account expires"""
        return max(0, self.remaining_days)

    @property
    def is_expired(self):
        """Check if account is expired"""
        return self.remaining_days <= 0

    @property
    def needs_payment_soon(self):
        """Check if payment needed within 7 days"""
        return self.remaining_days <= 7

    def add_payment(self, amount: float, days_added: int, payment_method: str = "manual",
                    reference_number: str = None, notes: str = None, processed_by: str = "admin"):
        """Process a new payment and add days to account"""
        from app.models.payment import Payment

        # Add days to account
        self.remaining_days += days_added

        # Update payment tracking
        self.last_payment_date = date.today()
        self.total_paid = (self.total_paid or 0) + amount

        # Update expiration date
        self.update_expiration_date()

        # Reactivate account if it was expired
        if not self.is_active and self.remaining_days > 0:
            self.is_active = True

        # Create payment record
        payment = Payment(
            learning_center_id=self.id,
            amount=amount,
            days_added=days_added,
            payment_date=date.today(),
            payment_method=payment_method,
            reference_number=reference_number,
            notes=notes,
            processed_by=processed_by,
            status="completed",
            is_processed=True
        )

        return payment

    def update_expiration_date(self):
        """Update expiration date based on remaining days"""
        if self.remaining_days > 0:
            self.expires_at = date.today() + timedelta(days=self.remaining_days)
        else:
            self.expires_at = date.today()

    def check_and_update_status(self):
        """Check account status and update is_active accordingly"""
        should_be_active = self.remaining_days > 0

        if self.is_active != should_be_active:
            self.is_active = should_be_active

        # Update expiration date
        self.update_expiration_date()

        return self.is_active

    def deduct_day(self):
        """Deduct one day from account (called daily by scheduler)"""
        if self.remaining_days > 0:
            self.remaining_days -= 1

        # Auto-deactivate if no days left
        if self.remaining_days <= 0:
            self.is_active = False

        self.update_expiration_date()
        return self.remaining_days

    def extend_trial(self, trial_days: int = 7, processed_by: str = "system"):
        """Add free trial days (no payment required)"""
        from app.models.payment import Payment

        self.remaining_days += trial_days
        self.update_expiration_date()

        if not self.is_active:
            self.is_active = True

        # Create a record for trial extension
        payment = Payment(
            learning_center_id=self.id,
            amount=0.00,
            days_added=trial_days,
            payment_date=date.today(),
            payment_method="trial",
            notes=f"Free trial extension: {trial_days} days",
            processed_by=processed_by,
            status="completed",
            is_processed=True
        )

        return payment

    def get_payment_history(self, limit: int = None):
        """Get payment history, most recent first"""
        payments = sorted(self.payments, key=lambda p: p.payment_date, reverse=True)
        if limit:
            return payments[:limit]
        return payments

    def calculate_monthly_cost(self):
        """Calculate average monthly cost based on payment history"""
        if not self.payments:
            return 0.0

        completed_payments = [p for p in self.payments if p.status == "completed"]
        if not completed_payments:
            return 0.0

        total_paid = sum(float(p.amount) for p in completed_payments)
        total_days = sum(p.days_added for p in completed_payments)

        if total_days == 0:
            return 0.0

        cost_per_day = total_paid / total_days
        return round(cost_per_day * 30, 2)  # Monthly cost