import gettext 

localedir = 'locale'
lang = 'es'

t = gettext.translation('programa', localedir, [lang], fallback=True)
_ = t.gettext

def custom_gettext(s):  
  current_dict = {
              'usage: ': _('Uso: '),
              'optional arguments': _('argumentos opcionales'),
              'show this help message and exit': _('muestra este mensaje de ayuda y sale'),
              'positional arguments': _('argumentos posicionales'),
              'the following arguments are required: %s': _('los siguientes argumentos son requeridos: %s'),
              'show program''s version number and exit': _('muestra la versión del programa y sale'),
              'expected one argument': _('se espera un valor para el parámetro'),
              'expected at least one argument': _('se espera al menos un valor para el parámetro')
  }
 
  if s in current_dict:
      return current_dict[s]
  return s
gettext.gettext = custom_gettext
