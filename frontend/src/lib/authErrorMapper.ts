export type AuthLanguage = 'DE' | 'TR' | 'ES' | 'EN';

export interface FormattedAuthError {
  message: string;
  field?: 'email' | 'password' | 'general';
}

/**
 * Maps Supabase Auth errors to human-readable, localized error messages.
 */
export function formatAuthError(err: any, lang: AuthLanguage = 'DE'): FormattedAuthError {
  if (!err) return { message: '', field: 'general' };

  const raw = typeof err === 'string' ? err : (err.message || err.error_description || String(err));
  const msg = raw.toLowerCase();
  const errorCode = (err.error_code || err.code || '').toLowerCase();

  // 1. Incorrect Password / Invalid Credentials
  if (
    msg.includes('invalid login credentials') ||
    msg.includes('invalid credentials') ||
    msg.includes('invalid_grant') ||
    errorCode === 'invalid_credentials'
  ) {
    switch (lang) {
      case 'TR':
        return {
          message: 'E-posta adresi veya şifre hatalı. Lütfen bilgilerinizi kontrol edip tekrar deneyin.',
          field: 'password'
        };
      case 'DE':
        return {
          message: 'E-Mail-Adresse oder Passwort ist falsch. Bitte überprüfen Sie Ihre Eingabe.',
          field: 'password'
        };
      case 'ES':
        return {
          message: 'Correo electrónico o contraseña incorrectos. Por favor verifique sus datos.',
          field: 'password'
        };
      case 'EN':
      default:
        return {
          message: 'Invalid email or password. Please check your login details and try again.',
          field: 'password'
        };
    }
  }

  // 2. Email Not Confirmed
  if (msg.includes('email not confirmed') || errorCode === 'email_not_confirmed') {
    switch (lang) {
      case 'TR':
        return {
          message: 'E-posta adresiniz henüz doğrulanmadı. Lütfen e-postanızdaki aktivasyon bağlantısını tıklayın.',
          field: 'email'
        };
      case 'DE':
        return {
          message: 'Ihre E-Mail-Adresse wurde noch nicht bestätigt. Bitte überprüfen Sie Ihr Postfach.',
          field: 'email'
        };
      case 'ES':
        return {
          message: 'Tu correo electrónico aún no ha sido confirmado. Por favor revisa tu bandeja de entrada.',
          field: 'email'
        };
      case 'EN':
      default:
        return {
          message: 'Your email address has not been confirmed yet. Please check your inbox.',
          field: 'email'
        };
    }
  }

  // 3. User Already Exists
  if (
    msg.includes('user already registered') ||
    msg.includes('already exists') ||
    errorCode === 'user_already_exists'
  ) {
    switch (lang) {
      case 'TR':
        return {
          message: 'Bu e-posta adresi ile zaten kayıtlı bir hesap var. Lütfen giriş yapın.',
          field: 'email'
        };
      case 'DE':
        return {
          message: 'Mit dieser E-Mail-Adresse existiert bereits ein Konto. Bitte melden Sie sich an.',
          field: 'email'
        };
      case 'ES':
        return {
          message: 'Ya existe una cuenta registrada con este correo electrónico. Inicie sesión.',
          field: 'email'
        };
      case 'EN':
      default:
        return {
          message: 'An account with this email already exists. Please log in.',
          field: 'email'
        };
    }
  }

  // 4. Rate Limiting / Too Many Attempts
  if (
    msg.includes('rate limit') ||
    msg.includes('too many requests') ||
    errorCode === 'over_email_send_rate_limit' ||
    errorCode === 'over_request_rate_limit'
  ) {
    switch (lang) {
      case 'TR':
        return {
          message: 'Çok fazla istek gönderildi. Güvenliğiniz için lütfen birkaç dakika bekleyip tekrar deneyin.',
          field: 'general'
        };
      case 'DE':
        return {
          message: 'Zu viele Versuche. Bitte warten Sie einen Moment und versuchen Sie es erneut.',
          field: 'general'
        };
      case 'ES':
        return {
          message: 'Demasiados intentos. Por favor espere unos minutos e intente de nuevo.',
          field: 'general'
        };
      case 'EN':
      default:
        return {
          message: 'Too many attempts. Please wait a few minutes before trying again.',
          field: 'general'
        };
    }
  }

  // 5. Weak Password
  if (msg.includes('password') && (msg.includes('6') || msg.includes('short') || msg.includes('weak'))) {
    switch (lang) {
      case 'TR':
        return {
          message: 'Şifreniz en az 6 karakter uzunluğunda olmalıdır.',
          field: 'password'
        };
      case 'DE':
        return {
          message: 'Das Passwort muss mindestens 6 Zeichen lang sein.',
          field: 'password'
        };
      case 'ES':
        return {
          message: 'La contraseña debe tener al menos 6 caracteres.',
          field: 'password'
        };
      case 'EN':
      default:
        return {
          message: 'Password must be at least 6 characters long.',
          field: 'password'
        };
    }
  }

  // 6. Generic Fallback
  switch (lang) {
    case 'TR':
      return {
        message: 'Giriş işlemi başarısız. Lütfen bilgilerinizi kontrol edip tekrar deneyin.',
        field: 'general'
      };
    case 'DE':
      return {
        message: 'Anmeldung fehlgeschlagen. Bitte überprüfen Sie Ihre Eingabe und versuchen Sie es erneut.',
        field: 'general'
      };
    case 'ES':
      return {
        message: 'No se pudo iniciar sesión. Por favor verifique sus datos e intente nuevamente.',
        field: 'general'
      };
    case 'EN':
    default:
      return {
        message: 'Authentication failed. Please check your details and try again.',
        field: 'general'
      };
  }
}
