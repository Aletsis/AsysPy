"""Entidad Employee y Enums de organización."""

from dataclasses import dataclass, field
from datetime import date
from enum import Enum
import re

from attendance.domain.common.exceptions import ValidationError
from attendance.domain.organization.fingerprint import Fingerprint

# Expresiones regulares para validaciones de formato
_EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@(?:[a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}$")
_CURP_REGEX = re.compile(
    r"^[A-Z]{4}\d{6}[HM]"
    r"(AS|BC|BS|CC|CL|CM|CS|CH|DF|DG|GT|GR|HG|JC|MC|MN|MS|NT|NL|OC|PL|QT|QR|SP|SL|SR|TC|TS|TL|VZ|YN|ZS|NE)"
    r"[B-DF-HJ-NP-TV-Z]{3}[A-Z\d]\d$"
)
_RFC_REGEX = re.compile(r"^[A-ZÑ&]{4}\d{6}[A-Z0-9]{3}$")
_PHONE_ALLOWED_CHARS = re.compile(r"^\+?[\d\s\-\(\)]+$")
_CARD_REGEX = re.compile(r"^[A-Za-z0-9_\-]{1,20}$")


class Sex(str, Enum):
    MALE = "male"
    FEMALE = "female"


@dataclass
class Employee:
    """Entidad que representa a un colaborador en el dominio organizacional."""

    id: int | None
    pin: str
    first_name: str
    paternal_last_name: str
    maternal_last_name: str | None
    hire_date: date
    sex: Sex
    department_id: int
    position: str
    home_branch_id: int
    active: bool = True
    email: str | None = None
    phone_number: str | None = None
    curp: str | None = None
    rfc: str | None = None
    password: str | None = None
    card_number: str | None = None
    fingerprints: list[Fingerprint] = field(default_factory=list)

    def __post_init__(self) -> None:
        self._normalize()
        self.validate()

    def _normalize(self) -> None:
        """Normaliza cadenas y tipos de datos antes de validar."""
        if self.pin is not None:
            self.pin = str(self.pin).strip()

        if self.first_name is not None:
            self.first_name = str(self.first_name).strip()

        if self.paternal_last_name is not None:
            self.paternal_last_name = str(self.paternal_last_name).strip()

        if self.maternal_last_name is not None:
            cleaned_maternal = str(self.maternal_last_name).strip()
            self.maternal_last_name = cleaned_maternal if cleaned_maternal else None

        if isinstance(self.sex, str) and not isinstance(self.sex, Sex):
            try:
                self.sex = Sex(self.sex.lower())
            except ValueError:
                pass  # La validación generará el ValidationError correspondiente

        if self.position is not None:
            self.position = str(self.position).strip()

        if self.email is not None:
            cleaned_email = str(self.email).strip().lower()
            self.email = cleaned_email if cleaned_email else ""

        if self.phone_number is not None:
            cleaned_phone = str(self.phone_number).strip()
            self.phone_number = cleaned_phone if cleaned_phone else ""

        if self.curp is not None:
            cleaned_curp = str(self.curp).strip().upper()
            self.curp = cleaned_curp if cleaned_curp else ""

        if self.rfc is not None:
            cleaned_rfc = str(self.rfc).strip().upper()
            self.rfc = cleaned_rfc if cleaned_rfc else ""

        if self.password is not None:
            cleaned_password = str(self.password).strip()
            self.password = cleaned_password if cleaned_password else ""

        if self.card_number is not None:
            cleaned_card = str(self.card_number).strip()
            self.card_number = cleaned_card if cleaned_card else ""

        if self.fingerprints is None:
            self.fingerprints = []

    def validate(self) -> None:
        """Valida exhaustivamente todos los atributos e invariantes de la entidad."""
        # Validación de ID
        if self.id is not None:
            if not isinstance(self.id, int) or isinstance(self.id, bool) or self.id <= 0:
                raise ValidationError("El ID de empleado debe ser un número entero positivo.")

        # Validación de PIN
        if not self.pin:
            raise ValidationError("El PIN de empleado no puede estar vacío.")
        if any(c.isspace() for c in self.pin):
            raise ValidationError("El PIN de empleado no puede contener espacios en blanco.")
        if len(self.pin) > 50:
            raise ValidationError("El PIN de empleado no puede exceder los 50 caracteres.")

        # Validación de Nombre(s)
        if not self.first_name:
            raise ValidationError("El nombre del empleado no puede estar vacío.")
        if len(self.first_name) > 100:
            raise ValidationError("El nombre del empleado no puede exceder los 100 caracteres.")

        # Validación de Apellido Paterno
        if not self.paternal_last_name:
            raise ValidationError("El apellido paterno del empleado no puede estar vacío.")
        if len(self.paternal_last_name) > 100:
            raise ValidationError("El apellido paterno del empleado no puede exceder los 100 caracteres.")

        # Validación de Apellido Materno (opcional)
        if self.maternal_last_name is not None and len(self.maternal_last_name) > 100:
            raise ValidationError("El apellido materno del empleado no puede exceder los 100 caracteres.")

        # Validación de Fecha de Contratación
        if not isinstance(self.hire_date, date):
            raise ValidationError("La fecha de ingreso debe ser una fecha válida.")

        # Validación de Sexo
        if not isinstance(self.sex, Sex):
            raise ValidationError(f"El sexo del empleado es inválido: {self.sex}. Debe ser 'male' o 'female'.")

        # Validación de Departamento
        if not isinstance(self.department_id, int) or isinstance(self.department_id, bool) or self.department_id <= 0:
            raise ValidationError("El ID de departamento debe ser un entero positivo.")

        # Validación de Puesto
        if not self.position:
            raise ValidationError("El puesto de trabajo no puede estar vacío.")
        if len(self.position) > 100:
            raise ValidationError("El puesto de trabajo no puede exceder los 100 caracteres.")

        # Validación de Sucursal Base
        if not isinstance(self.home_branch_id, int) or isinstance(self.home_branch_id, bool) or self.home_branch_id <= 0:
            raise ValidationError("El ID de sucursal base debe ser un entero positivo.")

        # Validación de Estado Activo
        if not isinstance(self.active, bool):
            raise ValidationError("El estado activo debe ser un valor booleano.")

        # Validación de Correo Electrónico (opcional)
        if self.email is not None:
            if not self.email:
                raise ValidationError("El correo electrónico no puede ser una cadena vacía.")
            if len(self.email) > 255:
                raise ValidationError("El correo electrónico no puede exceder los 255 caracteres.")
            if not _EMAIL_REGEX.match(self.email):
                raise ValidationError(f"El formato del correo electrónico es inválido: '{self.email}'.")

        # Validación de Número Telefónico (opcional)
        if self.phone_number is not None:
            if not self.phone_number:
                raise ValidationError("El número de teléfono no puede ser una cadena vacía.")
            if not _PHONE_ALLOWED_CHARS.match(self.phone_number):
                raise ValidationError(
                    f"El número de teléfono '{self.phone_number}' contiene caracteres inválidos. Solo se permiten dígitos, espacios, guiones y el prefijo '+'."
                )
            digits = re.sub(r"\D", "", self.phone_number)
            if not (10 <= len(digits) <= 15):
                raise ValidationError(
                    f"El número de teléfono debe contener entre 10 y 15 dígitos numéricos (actualmente tiene {len(digits)})."
                )

        # Validación de CURP (opcional)
        if self.curp is not None:
            if not self.curp:
                raise ValidationError("El CURP no puede ser una cadena vacía.")
            if len(self.curp) != 18:
                raise ValidationError(f"El CURP debe tener exactamente 18 caracteres (actualmente tiene {len(self.curp)}).")
            if not _CURP_REGEX.match(self.curp):
                raise ValidationError(f"El formato del CURP es inválido según el estándar oficial de RENAPO: '{self.curp}'.")

        # Validación de RFC (opcional)
        if self.rfc is not None:
            if not self.rfc:
                raise ValidationError("El RFC no puede ser una cadena vacía.")
            if len(self.rfc) != 13:
                raise ValidationError(f"El RFC de persona física debe tener exactamente 13 caracteres (actualmente tiene {len(self.rfc)}).")
            if not _RFC_REGEX.match(self.rfc):
                raise ValidationError(f"El formato del RFC es inválido según el estándar oficial del SAT: '{self.rfc}'.")

        # Validación de Contraseña para Checador (opcional)
        if self.password is not None:
            if not self.password:
                raise ValidationError("La contraseña para checador no puede ser una cadena vacía.")
            if not self.password.isdigit():
                raise ValidationError("La contraseña para registro en reloj checador debe ser exclusivamente numérica.")
            if not (1 <= len(self.password) <= 8):
                raise ValidationError(
                    f"La contraseña para checador debe tener entre 1 y 8 dígitos numéricos (actualmente tiene {len(self.password)})."
                )

        # Validación de Tarjeta RFID (opcional)
        if self.card_number is not None:
            if not self.card_number:
                raise ValidationError("El número de tarjeta no puede ser una cadena vacía.")
            if not _CARD_REGEX.match(self.card_number):
                raise ValidationError(
                    f"El número de tarjeta '{self.card_number}' debe contener entre 1 y 20 caracteres alfanuméricos sin espacios."
                )

        # Validación de Huellas Biométricas
        if not isinstance(self.fingerprints, list):
            raise ValidationError("La lista de huellas biométricas debe ser una lista.")
        if len(self.fingerprints) > 10:
            raise ValidationError("Un empleado no puede tener más de 10 huellas registradas (una por cada dedo).")

        seen_fingers: set[int] = set()
        for fp in self.fingerprints:
            if not isinstance(fp, Fingerprint):
                raise ValidationError("Cada elemento de la lista de huellas debe ser una instancia de Fingerprint.")
            if fp.finger_index in seen_fingers:
                raise ValidationError(f"Existe más de una huella registrada para el dedo con índice {fp.finger_index}.")
            seen_fingers.add(fp.finger_index)

    @property
    def full_name(self) -> str:
        """Nombre completo del colaborador."""
        parts = [self.first_name, self.paternal_last_name, self.maternal_last_name]
        return " ".join(p for p in parts if p)

    # ------------------------------------------------------------------------
    # Propiedades alias en español
    # ------------------------------------------------------------------------
    @property
    def correo(self) -> str | None:
        return self.email

    @correo.setter
    def correo(self, value: str | None) -> None:
        self.email = value
        self._normalize()
        self.validate()

    @property
    def telefono(self) -> str | None:
        return self.phone_number

    @telefono.setter
    def telefono(self, value: str | None) -> None:
        self.phone_number = value
        self._normalize()
        self.validate()

    @property
    def contrasena(self) -> str | None:
        return self.password

    @contrasena.setter
    def contrasena(self, value: str | None) -> None:
        self.password = value
        self._normalize()
        self.validate()

    @property
    def tarjeta(self) -> str | None:
        return self.card_number

    @tarjeta.setter
    def tarjeta(self, value: str | None) -> None:
        self.card_number = value
        self._normalize()
        self.validate()

    @property
    def huellas(self) -> list[Fingerprint]:
        return self.fingerprints

    @huellas.setter
    def huellas(self, value: list[Fingerprint]) -> None:
        self.fingerprints = value
        self._normalize()
        self.validate()

    # ------------------------------------------------------------------------
    # Métodos de gestión de huellas biométricas
    # ------------------------------------------------------------------------
    def add_fingerprint(self, fingerprint: Fingerprint) -> None:
        """Agrega o actualiza la plantilla de huella para el índice de dedo especificado."""
        if not isinstance(fingerprint, Fingerprint):
            raise ValidationError("El objeto a agregar debe ser una instancia de Fingerprint.")

        # Si ya existe para ese índice de dedo, reemplazarlo
        for i, existing in enumerate(self.fingerprints):
            if existing.finger_index == fingerprint.finger_index:
                self.fingerprints[i] = fingerprint
                return

        if len(self.fingerprints) >= 10:
            raise ValidationError("No se pueden registrar más de 10 huellas por colaborador.")

        self.fingerprints.append(fingerprint)

    def get_fingerprint(self, finger_index: int) -> Fingerprint | None:
        """Obtiene la huella biométrica registrada para el dedo indicado, o None si no existe."""
        for fp in self.fingerprints:
            if fp.finger_index == finger_index:
                return fp
        return None

    def remove_fingerprint(self, finger_index: int) -> bool:
        """Elimina la huella del índice indicado. Retorna True si existía y fue removida."""
        for i, fp in enumerate(self.fingerprints):
            if fp.finger_index == finger_index:
                del self.fingerprints[i]
                return True
        return False
