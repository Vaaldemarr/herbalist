from django.conf import settings
from django.conf.urls.i18n import is_language_prefix_patterns_used
from django.http import HttpResponseRedirect
from django.urls import get_script_prefix, is_valid_path
from django.utils import translation
from django.utils.cache import patch_vary_headers
from django.utils.deprecation import MiddlewareMixin

from django.utils import translation
from django.conf import settings
from django.utils.deprecation import MiddlewareMixin

def get_session_language(request):
    if hasattr(request, 'user'):
        if request.user.is_authenticated and hasattr(request.user, 'settings'):
            # Если пользователь авторизован и у него есть настройки
            return request.user.settings.language
        else:
            return request.LANGUAGE_CODE if not 'language' in request.session else request.session['language']
    else:
        return request.LANGUAGE_CODE

class MyLocaleMiddleware(MiddlewareMixin):
    def process_request(self, request):
        if hasattr(request, 'user') and request.user.is_authenticated and hasattr(request.user, 'settings'):
            # Если пользователь авторизован и у него есть настройки
            user_settings = request.user.settings  # Получение настроек текущего пользователя через related_name
            translation.activate(user_settings.language)
            request.LANGUAGE_CODE = user_settings.language
        else:
            language = request.session.get('language')
            if language:
                translation.activate(language)
                request.LANGUAGE_CODE = language
            else:
                translation.activate(settings.LANGUAGE_CODE)
                request.LANGUAGE_CODE = settings.LANGUAGE_CODE

class LocaleMiddleware(MiddlewareMixin):
    """
    Parse a request and decide what translation object to install in the
    current thread context. This allows pages to be dynamically translated to
    the language the user desires (if the language is available).
    """

    response_redirect_class = HttpResponseRedirect

    def process_request(self, request):
        urlconf = getattr(request, "urlconf", settings.ROOT_URLCONF)
        (
            i18n_patterns_used,
            prefixed_default_language,
        ) = is_language_prefix_patterns_used(urlconf)
        language = translation.get_language_from_request(
            request, check_path=i18n_patterns_used
        )
        language_from_path = translation.get_language_from_path(request.path_info)
        if (
            not language_from_path
            and i18n_patterns_used
            and not prefixed_default_language
        ):
            language = settings.LANGUAGE_CODE
        translation.activate(language)
        request.LANGUAGE_CODE = translation.get_language()

    def process_response(self, request, response):
        language = translation.get_language()
        language_from_path = translation.get_language_from_path(request.path_info)
        urlconf = getattr(request, "urlconf", settings.ROOT_URLCONF)
        (
            i18n_patterns_used,
            prefixed_default_language,
        ) = is_language_prefix_patterns_used(urlconf)

        if (
            response.status_code == 404
            and not language_from_path
            and i18n_patterns_used
            and prefixed_default_language
        ):
            # Maybe the language code is missing in the URL? Try adding the
            # language prefix and redirecting to that URL.
            language_path = "/%s%s" % (language, request.path_info)
            path_valid = is_valid_path(language_path, urlconf)
            path_needs_slash = not path_valid and (
                settings.APPEND_SLASH
                and not language_path.endswith("/")
                and is_valid_path("%s/" % language_path, urlconf)
            )

            if path_valid or path_needs_slash:
                script_prefix = get_script_prefix()
                # Insert language after the script prefix and before the
                # rest of the URL
                language_url = request.get_full_path(
                    force_append_slash=path_needs_slash
                ).replace(script_prefix, "%s%s/" % (script_prefix, language), 1)
                # Redirect to the language-specific URL as detected by
                # get_language_from_request(). HTTP caches may cache this
                # redirect, so add the Vary header.
                redirect = self.response_redirect_class(language_url)
                patch_vary_headers(redirect, ("Accept-Language", "Cookie"))
                return redirect

        if not (i18n_patterns_used and language_from_path):
            patch_vary_headers(response, ("Accept-Language",))
        response.headers.setdefault("Content-Language", language)
        return response
