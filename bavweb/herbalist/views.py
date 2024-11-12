from django.shortcuts import render, get_object_or_404
from django.template.loader import render_to_string

# Create your views here.
from django.http import HttpResponse, HttpResponseRedirect, HttpResponseNotFound
from django.urls import reverse

from django.db import connections, transaction, connection, models
from django.db.models import Prefetch
from django.db.models.functions import Lower

# from . import models_bav
from .models_bav import (
    Abbreviations, Abbreviationsreg, Biologicallyactivecompounds,
    Plants, PlantsNames, Families, Biologicalactivity, Chemicalcompoundsgroups,
    Biologicallyactivecompounds, BacBiologicalactivity, Languages
)

from .models import Mixtures, MixtureList

from django.contrib import messages

from django.contrib.auth.decorators import login_required

from django.contrib.auth.views import LoginView, LogoutView
from django.urls import reverse_lazy

from .users import UserUpdateView, UserSettingsForm

from django.core.paginator import Paginator

from django.conf import settings
from django.utils import translation

from .middleware import get_session_language

from .queries import QueryTexts, ReplaceText

from django.utils.translation import gettext as _

def start_page(request):
    lng_title = get_session_language(request)
    # cur_lang = get_object_or_404(Languages.objects.using('bav'), name=lng_title)
    # qt = QueryTexts(cur_lang)
    # rt = ReplaceText(cur_lang)
    lng_sel = {'language': lng_title, 'url': 'home', 'params': '?', 'id': '0'}

    # context = {'name': 'Django'}  # Данные для передачи в шаблон
    # return render(request, 'herbalist/hello1.html', context)
    context = {'active_page': '', 'lng': lng_sel}  # Данные для передачи в шаблон
    return render(request, 'herbalist/index.html', context)

def language_redirect(request, id, url, params):
    # form_id = request.POST.get('form_id')
    # if form_id == 'language_form':
    #     pass
    choice = request.POST.get('selected_language', '')
    set_session_language(request, choice)

    if id:
        return HttpResponseRedirect(reverse(url, args=(id,))+params)
    else:
        return HttpResponseRedirect(reverse(url)+params)

def set_language(request, lang_code, redirect_link):
    # Проверяем, что язык поддерживается
    if lang_code in dict(settings.LANGUAGES):
        # Активируем выбранный язык
        translation.activate(lang_code)
        
        # Сохраняем язык в сессии пользователя
        request.session[translation.LANGUAGE_SESSION_KEY] = lang_code
    
    # Перенаправляем пользователя (например, на главную страницу)
    return HttpResponseRedirect(reverse(redirect_link))

def get_page_settings(request):
    # Проверяем, авторизован ли пользователь и есть ли у него атрибут settings
    if request.user.is_authenticated and hasattr(request.user, 'settings'):
        # Если пользователь авторизован и у него есть настройки
        user_settings = request.user.settings  # Получение настроек текущего пользователя через related_name
        page_size = user_settings.page_size
        links_buttons = user_settings.page_buttons
    else:
        # Для неавторизованных пользователей или если нет настроек, используем значение по умолчанию
        page_size = 15  # или другое значение по умолчанию
        links_buttons = 4

    return page_size, links_buttons

def make_params_str(params: dict):
    result = ''
    n_param = 0
    for key, value in params.items():
        n_param += 1
        if n_param==1:
            result += '?'+key+'='
        else:
            result += '&'+key+'='
        if value != '' and value != None:
            result += str(value)

    # text_last_page = str(last_page) if last_page else ''
    # text_page_number = str(page_number) if page_number else ''
    # params_str = '?q={{ ' + query + ' }}&family={{ ' + family_query + \
    #             ' }}&last_page={{ ' + text_last_page + ' }}&page={{ ' + text_page_number + ' }}'

    return result

def make_detail_params_str(active_tab, queries: dict, pages_data: dict):
    result = ''

    if len(pages_data)==2:
        result = f"?{pages_data['Tab2']['cur_page']}={pages_data['Tab2']['cur_page_num']}"
        result += f"&{pages_data['Tab2']['other_page']}={pages_data['Tab2']['other_page_num']}"
        result += f"&active_tab={active_tab}"
        result += f"&q1={queries['q1']['text']}"
        result += f"&q2={queries['q2']['text']}"
        # result += f'&q3={queries['q3']['text']}'
    elif len(pages_data)==3:
        for tab_name, pg in pages_data.items():
            if tab_name == active_tab:
                result = f"?{pg['cur_page']}={pg['cur_page_num']}"
                result += f"&{pg['other_page']}={pg['other_page_num']}"
                result += f"&{pg['third_page']}={pg['third_page_num']}"
                result += f"&active_tab={active_tab}"
                result += f"&q1={queries['q1']['text']}"
                result += f"&q2={queries['q2']['text']}"
                result += f"&q3={queries['q3']['text']}"

    return result

def set_session_language(request, language):
    translation.activate(language)

    if hasattr(request, 'user'):
        if request.user.is_authenticated and hasattr(request.user, 'settings'):
            # Если пользователь авторизован и у него есть настройки
            request.user.settings.language = language
            request.user.settings.save()  # Сохраняем изменения в базе данных
    
    request.session['language'] = language
    request.LANGUAGE_CODE = language

def plants(request):
    page_size, links_buttons = get_page_settings(request)

    query = request.GET.get('q', '')  # Получаем поисковый запрос из формы
    family_query = request.GET.get('family', '')  # Получаем поисковый запрос для поиска по family
    # Получение текущей страницы из запроса
    page_number = request.GET.get('page')
    last_page = request.GET.get('last_page', 1)  # Последняя страница перед поиском

    lng_title = get_session_language(request)
    cur_lang = get_object_or_404(Languages.objects.using('bav'), name=lng_title)
    # lng = Languages.objects.using('bav').filter(name=lng_title).get()

    # Если запрос очищен (например, через reset кнопка)
    if request.GET.get('reset'):
        # Если сбрасываем поиск, используем последнюю страницу перед поиском
        page_number = request.GET.get('page1')

    plants_queryset = Plants.objects.using('bav').all().order_by('id')

    # Если есть поисковый запрос, фильтруем объекты по полям eng и rus
    # if query:
    #     plants_queryset = plants_queryset.filter(
    #         models.Q(eng__icontains=query) | models.Q(rus__icontains=query)
    #     )
    if query:
        if cur_lang.name == 'ru':
            filter = (models.Q(eng__icontains=query) | 
                      models.Q(rus__icontains=query) |
                      models.Q(rus__icontains=query.lower()) |
                      models.Q(rus__icontains=query.capitalize())
                      )
        else:
            # Фильтрация по полям PlantsNames
            filter = models.Q(eng__icontains=query) | models.Q(linked_names__name__icontains=query, linked_names__language=cur_lang.id) 
        plants_queryset = plants_queryset.filter(filter).distinct()
        # plants_queryset = plants_queryset.filter(
        #     models.Q(eng__icontains=query) | models.Q(rus__icontains=query) |
        #     models.Q(linked_names__name__icontains=query, linked_names__language=1)  # Фильтрация по полям PlantsNames
        # ).distinct()

      # Фильтрация по family (ищем по связанному объекту)
    if family_query:
        if cur_lang.name == 'ru':
            filter = (models.Q(family__eng__icontains=family_query) | 
                      models.Q(family__rus__icontains=family_query) |
                      models.Q(family__rus__icontains=family_query.lower()) | 
                      models.Q(family__rus__icontains=family_query.capitalize()))
        else:
            filter = models.Q(family__eng__icontains=family_query)
        plants_queryset = plants_queryset.filter(filter)
        # plants_queryset = plants_queryset.filter(family__name__icontains=family_query)
        # plants_queryset = plants_queryset.filter(
        #     models.Q(family__eng__icontains=family_query) | models.Q(family__rus__icontains=family_query)
        # )

  # Получаем все объекты Plants и устанавливаем пагинацию
    # plants_queryset = Plants.objects.using('bav').all()
    paginator = Paginator(plants_queryset, page_size)
    plants_page = paginator.get_page(page_number)

    if cur_lang.name == 'ru':
        plants_with_names = Plants.objects.using('bav').filter(id__in=[plant.id for plant in plants_page])
    else:
        # Заранее подгружаем все объекты PlantsNames, отфильтрованные по language
        plants_with_names = Plants.objects.using('bav').filter(id__in=[plant.id for plant in plants_page]).prefetch_related(
            Prefetch(
                'linked_names', # параметр related_name, указанный в атрибуте plant объекта
                queryset=PlantsNames.objects.using('bav').filter(language=cur_lang.id),
                to_attr='filtered_names'
            )
        )

    # Собираем данные для шаблона
    plants_data = []
    for plant in plants_with_names:
        # Если есть связанные объекты PlantsNames, используем первое значение из них, иначе - имя из Plants
        if cur_lang.name == 'ru':
            plant_name = plant.rus
            plant_family_name = plant.family.rus
        else:
            plant_name = plant.filtered_names[0].name if plant.filtered_names else plant.eng
            plant_family_name = plant.family.eng
        plants_data.append({
            'id': plant.id,
            'plant': plant,
            'display_name': plant_name,
            # 'rus': plant.rus,
            'lat': plant.eng,
            'family': plant.family,
            'family_name': plant_family_name,
            'spreading': plant.spreading,
        })

    get_params = {
        'q': query,
        'family': family_query,
        'last_page': last_page,
        'page': page_number
    }
    params_str = make_params_str(get_params)
    lng_sel = {'language': lng_title, 'url': 'plants', 'params': params_str, 'id': 0}

    return render(request, 'herbalist/plants.html', 
                  {'plants': plants_data, 'page_obj': plants_page, 
                   'links_buttons': links_buttons, 'links_buttons_left': -links_buttons, 
                   'query': query, 'family_query': family_query,
                   'last_page': last_page, 'active_page': 'plants',
                   'lng': lng_sel})


def check_queries(request, num_queries, use_my_q=False):

    qs = dict()
    for i in range(num_queries):
        qs[f'q{i+1}'] = request.GET.get(f'q{i+1}', '')  # Получаем поисковый запрос из формы

    reset_page = None
    reset_q = request.GET.get('reset_q')
    if reset_q:
        try:
            reset_page = int(reset_q.split('tab_page')[1])
        except:
            reset_page = None

    if reset_page:
        for i in range(num_queries):
            if reset_page == i+1:
                qs[f'q{i+1}'] = ''

    query_num = None
    if use_my_q:
        my_q = request.GET.get('my_q', '')  # Где введен поисковый запрос: на закладке Tab2 или Tab3
        if my_q in qs:
            for next_q in qs:
                if next_q != my_q:
                    qs[next_q] = ''


def plant_detail(request, id):
    page_size, links_buttons = get_page_settings(request)
    pg_size = page_size - 2

    lng_title = get_session_language(request)
    cur_lang = get_object_or_404(Languages.objects.using('bav'), name=lng_title)
    qt = QueryTexts(cur_lang)
    rt = ReplaceText(cur_lang)

    # Получение объекта Plant по id или 404, если объект не найден
    plant = get_object_or_404(Plants.objects.using('bav'), id=id)
    
    # # Получаем объект Plants по id
    # plant_obj = Plants.objects.get(pk=plant_id)  # Замените plant_id на реальное значение

    # Находим все записи в PlantsNames по plant и language
    plant_names = PlantsNames.objects.using('bav').filter(plant=plant, language=cur_lang.id) 
    local_names = []
    for plant_name in plant_names:
        local_names.append(plant_name.name)
        # print(plant_name)


    active_tab = request.GET.get('active_tab', 'Tab1')  # 'Main' по умолчанию, если параметр отсутствует

    # check_queries(request, 3, True)

    query1 = request.GET.get('q1', '')  # Получаем поисковый запрос из формы
    query2 = request.GET.get('q2', '')  # Получаем поисковый запрос для поиска

    reset_q = request.GET.get('reset_q')
    if reset_q == 'tab_page2':
        query1=''
    if reset_q == 'tab_page3':
        query2=''

    my_q = request.GET.get('my_q', '')  # Где введен поисковый запрос: на закладке Tab2 или Tab3
    if my_q == 'q1':
        query2 = ''
    elif my_q == 'q2':
        query1 = ''

    bac_ids = []
    bac_extra = dict()
    activity_ids = []
    activity_extra_data = []
    activity_extra = dict()

    if query2:
        query1 = ''
        bac_query, bac_params = qt.get_query('plant_bac_query', query2, id=id)
        # bac_query = """
        #     SELECT bp.bac, bp.extra
        #     FROM BAC_Plants AS bp
        #         LEFT JOIN
        #         BiologicallyActiveCompounds AS bc ON bc.id = bp.bac
        #     WHERE plant = %s AND 
        #         (bc.rus LIKE %s OR bc.rus LIKE %s OR 
        #             LOWER(bc.eng) LIKE LOWER(%s) );
        # """
        # with connections['bav'].cursor() as cursor:
        #     cursor.execute(bac_query, [id, 
        #                                   '%' + query2 + '%', 
        #                                   '%' + query2.capitalize() + '%', 
        #                                   '%' + query2 + '%', 
        #                                ])
        with connections['bav'].cursor() as cursor:
            cursor.execute(bac_query, bac_params)
            for row in cursor.fetchall():
                bac_ids.append(row[0])
                if lng_title=='ru':
                    bac_extra[row[0]] = row[1]
                else:
                    bac_extra[row[0]] =rt.replace_abbreviations(row[1])
        placeholders = ','.join(['%s'] * len(bac_ids))  # Создаем плейсхолдеры для каждого элемента списка
        activity_query = f"""
            SELECT DISTINCT BAC_BiologicalActivity.activity, text
            FROM BAC_Plants
            JOIN BAC_BiologicalActivity ON BAC_Plants.bac = BAC_BiologicalActivity.bac AND BAC_Plants.plant = {id}
            WHERE BAC_BiologicalActivity.bac IN({placeholders})
        """
        with connections['bav'].cursor() as cursor:
            cursor.execute(activity_query, bac_ids)
            for row in cursor.fetchall():
                activity_ids.append(row[0])
                activity_extra[row[0]]=row[1]
    elif not query1:
        # Первый запрос для получения bac (связанного Biologicallyactivecompounds)
        bac_query = """
            SELECT bac, extra
            FROM BAC_Plants
            WHERE plant = %s
        """
        with connections['bav'].cursor() as cursor:
            cursor.execute(bac_query, [id])
            # bac_ids = [row[0] for row in cursor.fetchall()]
            for row in cursor.fetchall():
                bac_ids.append(row[0])
                if lng_title=='ru':
                    bac_extra[row[0]] = row[1]
                else:
                    bac_extra[row[0]] = rt.replace_abbreviations(row[1])

    if query1:
        activity_query, activity_params = qt.get_query('plant_activity_query', query1, id=id)
        # activity_query = """
        #     SELECT DISTINCT ba.activity, ba.text
        #     FROM BAC_Plants AS bp
        #         JOIN
        #         BAC_BiologicalActivity AS ba ON bp.bac = ba.bac AND bp.plant = %s
        #         JOIN
        #         BiologicalActivity AS ba2 ON ba.activity = ba2.id
        #     WHERE ba2.rus LIKE %s OR ba2.rus LIKE %s OR LOWER(ba2.eng) LIKE LOWER(%s);
        # """
        # with connections['bav'].cursor() as cursor:
        #     cursor.execute(activity_query, [id, 
        #                                     '%' + query1 + '%', 
        #                                     '%' + query1.capitalize() + '%', 
        #                                     '%' + query1 + '%', 
        #                                 ])
        with connections['bav'].cursor() as cursor:
            cursor.execute(activity_query, activity_params)
            for row in cursor.fetchall():
                activity_ids.append(row[0])
                activity_extra[row[0]]=row[1]
        placeholders = ','.join(['%s'] * len(activity_ids))  # Создаем плейсхолдеры для каждого элемента списка
        bac_query = f"""
            SELECT bp.bac, bp.extra
            FROM BAC_Plants as bp
            JOIN BAC_BiologicalActivity as ba ON ba.bac=bp.bac AND bp.plant = {id}
            WHERE ba.activity IN ({placeholders})
        """
        with connections['bav'].cursor() as cursor:
            cursor.execute(bac_query, activity_ids)
            # bac_ids = [row[0] for row in cursor.fetchall()]
            for row in cursor.fetchall():
                bac_ids.append(row[0])
                # bac_extra[row[0]] = row[1]
                if lng_title=='ru':
                    bac_extra[row[0]] = row[1]
                else:
                    bac_extra[row[0]] = rt.replace_abbreviations(row[1])
    elif not query2:
        activity_query = """
            SELECT DISTINCT BAC_BiologicalActivity.activity, text
            FROM BAC_Plants
            LEFT JOIN BAC_BiologicalActivity ON BAC_Plants.bac = BAC_BiologicalActivity.bac
            WHERE BAC_Plants.plant = %s AND BAC_BiologicalActivity.activity IS NOT NULL
        """
        with connections['bav'].cursor() as cursor:
            cursor.execute(activity_query, [id])
            for row in cursor.fetchall():
                activity_ids.append(row[0])
                activity_extra[row[0]]=row[1]


    # Запрос объектов Biologicallyactivecompounds по bac_ids
    bac_objects = Biologicallyactivecompounds.objects.using('bav').filter(id__in=bac_ids).order_by('id')

    bac_page_obj, bac_page_obj2, bac_page_number = make_two_pages_for_details(cur_lang, 'bac',
        request, pg_size, bac_objects, 'tab_page3', bac_extra)    

    activity_objects = Biologicalactivity.objects.using('bav').filter(id__in=activity_ids).order_by('id')

    activity_page_obj, activity_page_obj2, activity_page_number = make_two_pages_for_details(cur_lang, 'activity',
        request, pg_size, activity_objects, 'tab_page2', activity_extra, True)

    activity_query = {
        'name': 'q1',
        'prompt': _('Search activity'),
        'text': query1
    }
    bac_query = {
        'name': 'q2',
        'prompt': _('Search compound'),
        'text': query2
    }

    activity_page = {
        'is_plant': False,
        'active_tab': 'Tab2',
        'cur_page': 'tab_page2',
        'cur_page_num': activity_page_number,
        'other_page': 'tab_page3',
        'other_page_num': bac_page_number,
        'tab_page_obj': activity_page_obj,
        'tab_page_obj2': activity_page_obj2
    }

    bac_page = {
        'is_plant': False,
        'active_tab': 'Tab3',
        'cur_page': 'tab_page3',
        'cur_page_num': bac_page_number,
        'other_page': 'tab_page2',
        'other_page_num': activity_page_number,
        'tab_page_obj': bac_page_obj,
        'tab_page_obj2': bac_page_obj2
    }

    queries = {activity_query['name']: activity_query, bac_query['name']: bac_query}
    pages_data = {activity_page['active_tab']:activity_page, bac_page['active_tab']: bac_page}
    params_str = make_detail_params_str(active_tab, queries, pages_data)
    lng_sel = {'language': get_session_language(request), 'url': 'plant_detail', 'params': params_str, 'id': id}

    plant_name = get_plant_name(plant, cur_lang)
    if lng_title=='ru':
        tab_captions = ['Описание', 'Активность' , 'Соединения']
        family_name = plant.family.rus
    else:
        tab_captions = ['Main', 'Activities' , 'Compounds']
        family_name = plant.family.eng

    return render(request, 'herbalist/plant_detail.html', 
                  {'plant': plant, 'plant_name': plant_name, 'names': local_names,
                   'family_name': family_name,
                   'q1': activity_query, 'q2': bac_query,
                   'tab2': activity_page, 'tab3': bac_page,
                   'active_tab': active_tab,
                   'tab_captions': tab_captions,
                   'active_page': 'plants', 'lng':lng_sel})

def split_long_name(name):
    long_name = name.split()
    if long_name and len(long_name)>1:
        if long_name[0][-1]==',' or long_name[0][-1]==';':
            short_name = long_name[0][:-1]
            alt = name[len(short_name)+2:]
        elif long_name[1][-1]==',' or long_name[1][-1]==';':
            short_name = f'{long_name[0]} {long_name[1][:-1]}'
            alt = name[len(long_name[0])+len(long_name[1])+2:]
        else:
            short_name = name
            alt = ''
    else:
        short_name = name
        alt = ''

    return (short_name, alt)

def compounds(request):

    page_size, links_buttons = get_page_settings(request)
    
    query = request.GET.get('q', '')  # Получаем поисковый запрос из формы
    cgroup = request.GET.get('g', '')  # Получаем поисковый запрос из формы
    # Получение текущей страницы из запроса
    page_number = request.GET.get('page')
    last_page = request.GET.get('last_page', 1)  # Последняя страница перед поиском
    
    lng_title = get_session_language(request)
    cur_lang = get_object_or_404(Languages.objects.using('bav'), name=lng_title)

    # Если запрос очищен (например, через reset кнопка)
    if request.GET.get('reset'):
        # Если сбрасываем поиск, используем последнюю страницу перед поиском
        page_number = request.GET.get('page1')

    catalog_queryset = Biologicallyactivecompounds.objects.using('bav').all().order_by('id')

    # Если есть поисковый запрос, фильтруем объекты по полям eng и rus
    if query:
        if cur_lang.name == 'ru':
            filter = (models.Q(eng__icontains=query) | 
                models.Q(rus__icontains=query) |
                models.Q(rus__icontains=query.lower()) |
                models.Q(rus__icontains=query.capitalize()) |
                models.Q(rus_alt__icontains=query))
        else:
            filter = models.Q(eng__icontains=query)
        catalog_queryset = catalog_queryset.filter(filter)
            

    if cgroup:
        if cur_lang.name == 'ru':
            filter = (models.Q(compounds_group__eng__icontains=cgroup) | 
                      models.Q(compounds_group__rus__icontains=cgroup) |
                      models.Q(compounds_group__rus__icontains=cgroup.lower()) |
                      models.Q(compounds_group__rus__icontains=cgroup.capitalize()))
        else:
            filter = models.Q(compounds_group__eng__icontains=cgroup)
        catalog_queryset = catalog_queryset.filter(filter)

    # Если есть поисковый запрос, фильтруем объекты по полям eng и rus текущего объекта и связанных объектов через compounds_group
    # if query:
    #     catalog_queryset = catalog_queryset.filter(
    #         models.Q(eng__icontains=query) | models.Q(rus__icontains=query) |
    #         models.Q(compounds_group__eng__icontains=query) | models.Q(compounds_group__rus__icontains=query)
    #     )

    # Получаем все объекты и устанавливаем пагинацию
    paginator = Paginator(catalog_queryset, page_size)
    catalog_page = paginator.get_page(page_number)

    # plants_with_names = Biologicallyactivecompounds.objects.using('bav').filter(id__in=[compound.id for compound in catalog_page])
    compound_data = []
    if cur_lang.name == 'ru':
        for compound in catalog_page:
            compound_see = None if compound.see==None else compound.see.rus
            compound_group = None if compound.compounds_group==None else compound.compounds_group.rus
            compound_data.append({'id': compound.id, 'name': compound.rus, 
                                  'compounds_group': compound_group,
                                  'see': compound_see, 'see_long': compound_see,
                                  'alt': compound.rus_alt})
    else:
        for compound in catalog_page:
            compound_see = None if compound.see==None else compound.see.eng
            compound_group = None if compound.compounds_group==None else compound.compounds_group.eng
            compound_name, alt = split_long_name(compound.eng)
            if compound_see:
                see_short, _ = split_long_name(compound_see)
            else:
                see_short = compound_see
            compound_data.append({'id': compound.id, 'name': compound_name, 
                                  'compounds_group': compound_group,
                                  'see': see_short, 'see_long': compound_see, 
                                  'alt': alt})

    get_params = {
        'q': query,
        'g': cgroup,
        'last_page': last_page,
        'page': page_number
    }
    params_str = make_params_str(get_params)
    lng_sel = {'language': lng_title, 'url': 'compounds', 'params': params_str, 'id': 0}

    return render(request, 'herbalist/compounds.html', 
                  {'page_obj': catalog_page, 'compounds': compound_data, 
                   'links_buttons': links_buttons, 'links_buttons_left': -links_buttons, 
                   'query': query, 'cgroup': cgroup, 'last_page': last_page,
                   'active_page': 'compounds',
                   'lng': lng_sel})

def make_two_pages_for_details(lng: Languages, item_type, request, pg_size, orm_objects, tab_page, extra_data, check_a=False):
    orm_paginator = Paginator(orm_objects, pg_size)
    page_number = request.GET.get(tab_page, 1)
    # if page_number=='' or page_number=='None':
    #     page_number=1
    try:
        page_number = int(page_number)
    except:
        page_number = 1
    if page_number > orm_paginator.num_pages:
        page_number = orm_paginator.num_pages
    elif page_number < 1:
        page_number=1
    page_obj = orm_paginator.get_page(page_number)
    page_obj.has_extra_data = False
    for next_item in page_obj:
        if lng.name == 'ru':
            next_item.display_name = next_item.rus
        else:
            if item_type=='bac':
                next_item.display_name, _ = split_long_name(next_item.eng)
            elif item_type=='plant':
                first_name = next_item.linked_names.filter(language_id=lng.id).first()
                if first_name:
                    next_item.display_name = first_name.name
                else:
                    next_item.display_name = next_item.eng
            else:
                next_item.display_name = next_item.eng
        if next_item.id in extra_data.keys():
            if item_type=='activity' and lng.name != 'ru':
                continue
            if check_a and extra_data[next_item.id]==next_item.name:
                continue
            if not page_obj.has_extra_data:
                page_obj.has_extra_data=True
            next_item.extra_data = extra_data[next_item.id]

    if int(page_number) < orm_paginator.num_pages:
        page_obj2 = orm_paginator.get_page(int(page_number)+1)
        page_obj2.has_extra_data = False
        for next_item in page_obj2:
            if lng.name == 'ru':
                next_item.display_name = next_item.rus
            else:
                if item_type=='bac':
                    next_item.display_name, _ = split_long_name(next_item.eng)
                elif item_type=='plant':
                    first_name = next_item.linked_names.filter(language_id=lng.id).first()
                    if first_name:
                        next_item.display_name = first_name.name
                    else:
                        next_item.display_name = next_item.eng
                else:
                    next_item.display_name = next_item.eng
            if next_item.id in extra_data.keys():
                if item_type=='activity' and lng.name != 'ru':
                    continue
                if check_a and extra_data[next_item.id]==next_item.name:
                    continue
                if not page_obj2.has_extra_data:
                    page_obj2.has_extra_data=True
                next_item.extra_data = extra_data[next_item.id]
    else:
        page_obj2 = None

    return page_obj, page_obj2, page_number

def make_two_mixture_pages_for_details(lng: Languages, request, pg_size, orm_objects, tab_page, extra_data, search_text='', check_a=False):
    selected = {mix_item.plant_id: mix_item.selected for mix_item in orm_objects}

    if search_text:
        if lng.name == 'ru':
            # Ваш запрос с регистронезависимыми фильтрами на поля 'rus', 'eng' и 'name'
            plants_obj = Plants.objects.using('bav').filter(
                models.Q(rus__icontains=search_text) | models.Q(rus__icontains=search_text.capitalize())
                | models.Q(eng__icontains=search_text)  # Регистронезависимый фильтр для rus и eng
            ).filter(id__in=[mix_item.plant_id for mix_item in orm_objects]).order_by('id')
        else:
            # Получаем все plant_ids, которые соответствуют поиску в поле `name` таблицы PlantsNames
            matching_plant_ids = PlantsNames.objects.using('bav').filter(
                models.Q(name__icontains=search_text),
                language=lng.id
            ).values('plant')  # Только plant_ids        
            # Ваш запрос с регистронезависимыми фильтрами на поля 'rus', 'eng' и 'name'
            plants_obj = Plants.objects.using('bav').filter(
                models.Q(rus__icontains=search_text) | models.Q(rus__icontains=search_text.capitalize())
                | models.Q(eng__icontains=search_text) | models.Q(id__in=models.Subquery(matching_plant_ids))  # Регистронезависимый фильтр для rus и eng
            ).filter(
                id__in=[mix_item.plant_id for mix_item in orm_objects]
            ).prefetch_related(
                Prefetch(
                    'linked_names',  # Параметр related_name, указанный в атрибуте plant объекта
                    queryset=PlantsNames.objects.using('bav').filter(
                        models.Q(language=1)
                    ),
                    to_attr='filtered_names'
                )
            ).distinct().order_by('id')
    else:
        if lng.name == 'ru':
            plants_obj = Plants.objects.using('bav').filter(id__in=[mix_item.plant_id for mix_item in orm_objects]).order_by('id')
        else:
            # Заранее подгружаем все объекты PlantsNames, отфильтрованные по language
            plants_obj = Plants.objects.using('bav').filter(id__in=[mix_item.plant_id for mix_item in orm_objects]).prefetch_related(
                Prefetch(
                    'linked_names', # параметр related_name, указанный в атрибуте plant объекта
                    queryset=PlantsNames.objects.using('bav').filter(language=1),
                    to_attr='filtered_names'
                )
            ).distinct().order_by('id')

    orm_paginator = Paginator(plants_obj, pg_size)

    # plants_paginator = Paginator(mixture_plants, pg_size * 2)  # Пагинация для списка растений
    # plant_page_number = request.GET.get('tab_page1')
    # plants_page_obj = plants_paginator.get_page(plant_page_number)

    page_number = request.GET.get(tab_page, 1)
    # if page_number=='' or page_number=='None':
    #     page_number=1
    try:
        page_number = int(page_number)
    except:
        page_number = 1
    if page_number > orm_paginator.num_pages:
        page_number = orm_paginator.num_pages
    elif page_number < 1:
        page_number=1

    page_obj = orm_paginator.get_page(page_number)

    # for plant_wn in page_obj:
    #     plant_wn.plant_name = plant_wn.filtered_names[0].name if plant_wn.filtered_names else plant_wn.name
    #     plant_wn.selected = selected[plant_wn.id]

    page_obj.has_extra_data = False
    for next_item in page_obj:
        if lng.name == 'ru':
            next_item.plant_name = next_item.rus
        else:
            next_item.plant_name = next_item.filtered_names[0].name if next_item.filtered_names else next_item.eng
        next_item.isel = selected[next_item.id]
        if next_item.id in extra_data.keys():
            if check_a and extra_data[next_item.id]==next_item.name:
                continue
            if not page_obj.has_extra_data:
                page_obj.has_extra_data=True
            next_item.extra_data = extra_data[next_item.id]

    if int(page_number) < orm_paginator.num_pages:
        page_obj2 = orm_paginator.get_page(int(page_number)+1)
        page_obj2.has_extra_data = False
        for next_item in page_obj2:
            if lng.name == 'ru':
                next_item.plant_name = next_item.rus
            else:
                next_item.plant_name = next_item.filtered_names[0].name if next_item.filtered_names else next_item.eng
            # next_item.plant_name = next_item.filtered_names[0].name if next_item.filtered_names else next_item.name
            next_item.isel = selected[next_item.id]
            if next_item.id in extra_data.keys():
                if check_a and extra_data[next_item.id]==next_item.name:
                    continue
                if not page_obj2.has_extra_data:
                    page_obj2.has_extra_data=True
                next_item.extra_data = extra_data[next_item.id]
    else:
        page_obj2 = None


    return page_obj, page_obj2, page_number

def compounds_detail(request, id):
    # Получение объекта Plant по id или 404, если объект не найден
    item = get_object_or_404(Biologicallyactivecompounds.objects.using('bav'), id=id)
    
    page_size, links_buttons = get_page_settings(request)
    pg_size = page_size - 2

    lng_title = get_session_language(request)
    cur_lang = get_object_or_404(Languages.objects.using('bav'), name=lng_title)
    qt = QueryTexts(cur_lang)
    rt = ReplaceText(cur_lang)

    active_tab = request.GET.get('active_tab', 'Tab1')  # 'Main' по умолчанию, если параметр отсутствует
    # selected_tab  = request.GET.get('tabs')

    query1 = request.GET.get('q1', '')  # Получаем поисковый запрос из формы
    query2 = request.GET.get('q2', '')  # Получаем поисковый запрос для поиска

    reset_q = request.GET.get('reset_q')
    if reset_q == 'tab_page2':
        query1=''
    if reset_q == 'tab_page3':
        query2=''

    plant_ids = []
    plant_extra = dict()
    if query2:
        plant_query, plant_params = qt.get_query('compounds_plant_query', query2, id=id)
        # plant_query = """
        # SELECT DISTINCT BAC_Plants.plant
        # FROM BAC_Plants
        #     LEFT JOIN
        #     Plants ON BAC_Plants.plant = Plants.id
        #     LEFT JOIN
        #     Plants_Names ON BAC_Plants.plant = Plants_Names.plant AND Plants_Names.language=1
        # WHERE BAC_Plants.bac = %s AND 
        #     (Plants.rus LIKE %s OR Plants.rus LIKE %s OR
        #      LOWER(Plants.eng) LIKE LOWER(%s) OR
        #      LOWER(Plants_Names.name) LIKE LOWER(%s))
        # """
        # with connections['bav'].cursor() as cursor:
        #     cursor.execute(plant_query, [id,
        #                                   '%' + query2 + '%', 
        #                                   '%' + query2.capitalize() + '%', 
        #                                   '%' + query2 + '%',
        #                                   '%' + query2 + '%',
        #                                   ])
        with connections['bav'].cursor() as cursor:
            cursor.execute(plant_query, plant_params)
            plant_ids = [row[0] for row in cursor.fetchall()]
        # plant_objects = plant_objects.using('bav').filter(id__in=plant_ids).order_by('id')
    else:
        plant_query = """
            SELECT plant, extra
            FROM BAC_Plants
            WHERE bac = %s
        """
        with connections['bav'].cursor() as cursor:
            cursor.execute(plant_query, [id])
            for row in cursor.fetchall():
                plant_ids.append(row[0])
                if row[1]:
                    # plant_extra[row[0]]=row[1]
                    if lng_title=='ru':
                        plant_extra[row[0]] = row[1]
                    else:
                        plant_extra[row[0]] =rt.replace_abbreviations(row[1])

    plant_objects = Plants.objects.using('bav').filter(id__in=plant_ids).order_by('id')

    plant_page_obj, plant_page_obj2, plant_page_number = make_two_pages_for_details(cur_lang, 'plant',
        request, pg_size, plant_objects, 'tab_page3', plant_extra)    

    activity_ids = []
    activity_extra_data = []
    activity_extra = dict()
    if query1:
        activity_query, activity_params = qt.get_query('compounds_activity_query', query1, id=id)
        # activity_query = """
        # SELECT ba.activity, ba2.name
        # FROM BAC_BiologicalActivity AS ba
        #     LEFT JOIN
        #     BiologicalActivity AS ba2 ON ba2.id = ba.activity
        # WHERE ba.bac = %s AND 
        #     (ba2.eng LIKE %s OR ba2.rus LIKE %s OR
        #     ba2.eng LIKE %s OR ba2.rus LIKE %s);
        # """
        # with connections['bav'].cursor() as cursor:
        #     cursor.execute(activity_query, [id, 
        #                                     '%' + query1 + '%', 
        #                                     '%' + query1 + '%',
        #                                     '%' + query1.capitalize() + '%', 
        #                                     '%' + query1.capitalize() + '%'
        #                                     ])
        with connections['bav'].cursor() as cursor:
            cursor.execute(activity_query, activity_params)
            activity_ids = [row[0] for row in cursor.fetchall()]
    else:
        activity_query = """
            SELECT activity, text
            FROM BAC_BiologicalActivity
            WHERE bac = %s
        """
        with connections['bav'].cursor() as cursor:
            cursor.execute(activity_query, [id])
            for row in cursor.fetchall():
                if row[0]==None:
                    activity_extra_data.append(row[1])
                else:
                    activity_ids.append(row[0])
                    activity_extra[row[0]]=row[1]

    activity_objects = Biologicalactivity.objects.using('bav').filter(id__in=activity_ids).order_by('id')

    activity_page_obj, activity_page_obj2, activity_page_number = make_two_pages_for_details(cur_lang, 'activity',
        request, pg_size, activity_objects, 'tab_page2', activity_extra, True)    

    activity_query = {
        'name': 'q1',
        'prompt': _('Search activity'),
        'text': query1
    }
    plant_query = {
        'name': 'q2',
        'prompt': _('Search plant'),
        'text': query2
    }

    activity_page = {
        'is_plant': False,
        'active_tab': 'Tab2',
        'cur_page': 'tab_page2',
        'cur_page_num': activity_page_number,
        'other_page': 'tab_page3',
        'other_page_num': plant_page_number,
        'tab_page_obj': activity_page_obj,
        'tab_page_obj2': activity_page_obj2
    }

    plant_page = {
        'is_plant': True,
        'active_tab': 'Tab3',
        'cur_page': 'tab_page3',
        'cur_page_num': plant_page_number,
        'other_page': 'tab_page2',
        'other_page_num': activity_page_number,
        'tab_page_obj': plant_page_obj,
        'tab_page_obj2': plant_page_obj2
    }

    queries = {activity_query['name']: activity_query, plant_query['name']: plant_query}
    pages_data = {activity_page['active_tab']:activity_page, plant_page['active_tab']: plant_page}
    params_str = make_detail_params_str(active_tab, queries, pages_data)
    lng_sel = {'language': lng_title, 'url': 'compounds_detail', 'params': params_str, 'id': id}


    if lng_title == 'ru':
        tab_captions = ['Описание', 'Активность' , 'Растения']
    else:
        tab_captions = ['Main', 'Activities' , 'Plants']

    item_captions = dict()
    if lng_title == 'ru':
        item_captions['shelf_name'] = item.rus
        item_captions['name'] = item.rus
        if item.compounds_group:
            item_captions['group_name'] = item.compounds_group.rus
            if item.compounds_group_text and item_captions['group_name'] != item.compounds_group_text:
                item_captions['group_text'] = item.compounds_group_text
        if item.see:
            item_captions['see'] = item.see.rus
        if item.note:
            item_captions['note'] = item.note
        if item.comment:
            item_captions['comment'] = item.comment
        if item.rus_alt:
            item_captions['rus_alt'] = item.rus_alt
        if item.biological_activity_extra:
            item_captions['activity_extra'] = item.biological_activity_extra
        if item.chemical_compound:
            item_captions['chemical_compound'] = item.chemical_compound.name
    else:
        short_name, _n = split_long_name(item.eng)
        item_captions['shelf_name'] = short_name
        item_captions['name'] = item.eng
        if item.compounds_group:
            item_captions['group_name'] = item.compounds_group.eng
        if item.see:
            item_captions['see'] = item.see.eng
        activity_extra_data = dict()

    return render(request, 'herbalist/compounds_detail.html', 
                  {'compounds': item, 'captions': item_captions,
                   'tab1_extra': activity_extra_data,
                   'q1': activity_query, 'q2': plant_query,
                   'tab2': activity_page, 'tab3': plant_page,
                   'active_tab': active_tab,
                   'tab_captions': tab_captions,
                   'active_page': 'compounds', 'lng': lng_sel})


def compounds_groups0(request):
    if request.method == 'POST':
        choice = request.POST.get('language', '')
        if choice:
            context = {'active_page': 'compounds-groups', 'lang': choice}
            return render(request, 'herbalist/index.html', context)
        
    context = {'active_page': 'compounds-groups'}
    return render(request, 'herbalist/index.html', context)

def compounds_groups(request):
    page_size, links_buttons = get_page_settings(request)
    
    query = request.GET.get('q', '')  # Получаем поисковый запрос из формы
    # Получение текущей страницы из запроса
    page_number = request.GET.get('page')
    last_page = request.GET.get('last_page', 1)  # Последняя страница перед поиском

    lng_title = get_session_language(request)
    cur_lang = get_object_or_404(Languages.objects.using('bav'), name=lng_title)

    # Если запрос очищен (например, через reset кнопка)
    if request.GET.get('reset'):
        # Если сбрасываем поиск, используем последнюю страницу перед поиском
        page_number = request.GET.get('page1')

    catalog_queryset = Chemicalcompoundsgroups.objects.using('bav').all().order_by('id')

    # Если есть поисковый запрос, фильтруем объекты по полям eng и rus
    if query:
        if cur_lang.name == 'ru':
            filter = (models.Q(rus__icontains=query) |
                      models.Q(rus__icontains=query.lower()) |
                      models.Q(rus__icontains=query.capitalize()))
        else:
            filter = models.Q(eng__icontains=query)
        catalog_queryset = catalog_queryset.filter(filter)

    # Получаем все объекты и устанавливаем пагинацию
    paginator = Paginator(catalog_queryset, page_size)
    catalog_page = paginator.get_page(page_number)

    for page_item in catalog_page:
        if cur_lang.name == 'ru':
            page_item.display_name = page_item.rus
        else:
            page_item.display_name = page_item.eng

    get_params = {
        'q': query,
        'last_page': last_page,
        'page': page_number
    }
    params_str = make_params_str(get_params)
    lng_sel = {'language': lng_title, 'url': 'compounds-groups', 'params': params_str, 'id': 0}

    return render(request, 'herbalist/compounds_groups.html', 
                  {'page_obj': catalog_page, 
                   'links_buttons': links_buttons, 'links_buttons_left': -links_buttons, 
                   'query': query, 'last_page': last_page,
                   'active_page': 'compounds-groups',
                   'lng': lng_sel})

def compounds_group_detail(request, id):
    # Получение объекта Plant по id или 404, если объект не найден
    item = get_object_or_404(Chemicalcompoundsgroups.objects.using('bav'), id=id)
    
    lng_title = get_session_language(request)
    # cur_lang = get_object_or_404(Languages.objects.using('bav'), name=lng_title)
    # qt = QueryTexts(cur_lang)
    # rt = ReplaceText(cur_lang)

    lng_sel = {'language': lng_title, 'url': 'compounds_group_detail', 'params': '?', 'id': id}

    if lng_title == 'ru':
        compounds_group_name = item.rus
    else:
        compounds_group_name = item.eng

    # Передача объекта plant в шаблон
    return render(request, 'herbalist/compounds_group_detail.html', {'compounds_group': item, 'compounds_group_name':compounds_group_name,
                                                                     'active_page': 'compounds-groups', 'lng': lng_sel})

def activities0(request):
    if request.method == 'POST':
        choice = request.POST.get('language', '')
        if choice:
            context = {'active_page': 'activities', 'lang': choice}
            return render(request, 'herbalist/index.html', context)
        
    context = {'active_page': 'activities'}
    return render(request, 'herbalist/index.html', context)

def activities(request):
    page_size, links_buttons = get_page_settings(request)
    
    query = request.GET.get('q', '')  # Получаем поисковый запрос из формы
    # Получение текущей страницы из запроса
    page_number = request.GET.get('page')
    last_page = request.GET.get('last_page', 1)  # Последняя страница перед поиском

    lng_title = get_session_language(request)
    cur_lang = get_object_or_404(Languages.objects.using('bav'), name=lng_title)

    # Если запрос очищен (например, через reset кнопка)
    if request.GET.get('reset'):
        # Если сбрасываем поиск, используем последнюю страницу перед поиском
        page_number = request.GET.get('page1')

    catalog_queryset = Biologicalactivity.objects.using('bav').all().order_by('id')

    # Если есть поисковый запрос, фильтруем объекты по полям eng и rus
    if query:
        if cur_lang.name == 'ru':
            filter = (models.Q(rus__icontains=query) |
                      models.Q(rus__icontains=query.lower()) |
                      models.Q(rus__icontains=query.capitalize()))
        else:
            filter = models.Q(eng__icontains=query)
        catalog_queryset = catalog_queryset.filter(filter)

    # Получаем все объекты и устанавливаем пагинацию
    paginator = Paginator(catalog_queryset, page_size)
    catalog_page = paginator.get_page(page_number)

    for page_item in catalog_page:
        if cur_lang.name == 'ru':
            page_item.display_name = page_item.rus
        else:
            page_item.display_name = page_item.eng

    get_params = {
        'q': query,
        'last_page': last_page,
        'page': page_number
    }
    params_str = make_params_str(get_params)
    lng_sel = {'language': lng_title, 'url': 'activities', 'params': params_str, 'id': 0}

    return render(request, 'herbalist/activities.html', 
                  {'page_obj': catalog_page, 
                   'links_buttons': links_buttons, 'links_buttons_left': -links_buttons, 
                   'query': query, 'last_page': last_page,
                   'active_page': 'activities',
                   'lng': lng_sel})

def activity_detail(request, id):
    page_size, links_buttons = get_page_settings(request)
    pg_size = page_size - 2

    # Получение объекта Plant по id или 404, если объект не найден
    activity_item = get_object_or_404(Biologicalactivity.objects.using('bav'), id=id)
    
    lng_title = get_session_language(request)
    cur_lang = get_object_or_404(Languages.objects.using('bav'), name=lng_title)
    qt = QueryTexts(cur_lang)
    rt = ReplaceText(cur_lang)

    active_tab = request.GET.get('active_tab', 'Tab1')

    query1 = request.GET.get('q1', '')  # Получаем поисковый запрос на закладке Tab2
    query2 = request.GET.get('q2', '')  # Получаем поисковый запрос на закладке Tab3

    reset_q = request.GET.get('reset_q')
    if reset_q == 'tab_page2': # Очиста поиска на закладке Tab2
        query1=''
    if reset_q == 'tab_page3': # Очиста поиска на закладке Tab3
        query2=''

    my_q = request.GET.get('my_q', '')  # Где введен поисковый запрос: на закладке Tab или Tab3
    if my_q == 'q1':
        query2 = ''
    elif my_q == 'q2':
        query1 = ''

    bac_ids = []
    plant_ids = []
    plant_extra = dict()

    if query1:
        # reset_q = 'tab_page3' # Очищаем второй поисковый запрос
        query2 = ''
        bac_query, bac_params = qt.get_query('activity_bac_query', query1, id=id)
        # bac_query = """
        #     SELECT bba.bac
        #     FROM BAC_BiologicalActivity as bba
        #     LEFT JOIN BiologicallyActiveCompounds as compound ON compound.id=bba.bac
        #     WHERE bba.activity = %s AND 
        #     (compound.rus LIKE %s OR compound.rus LIKE %s OR
        #     LOWER(compound.eng) LIKE LOWER(%s))
        # """
        # with connections['bav'].cursor() as cursor:
        #     cursor.execute(bac_query, [id, 
        #                                   '%' + query1 + '%', 
        #                                   '%' + query1.capitalize() + '%', 
        #                                   '%' + query1 + '%', 
        #                                ])
        with connections['bav'].cursor() as cursor:
            cursor.execute(bac_query, bac_params)
            bac_ids = [row[0] for row in cursor.fetchall()]
        placeholders = ','.join(['%s'] * len(bac_ids))  # Создаем плейсхолдеры для каждого элемента списка
        plant_query = f"""
            SELECT bp.plant, bp.extra
            FROM BAC_Plants AS bp
            WHERE bp.bac IN ({placeholders})
            """
        with connections['bav'].cursor() as cursor:
            cursor.execute(plant_query, bac_ids)
            for row in cursor.fetchall():
                plant_ids.append(row[0])
                if row[1]:
                    # plant_extra[row[0]] = row[1]
                    if lng_title=='ru':
                        plant_extra[row[0]] = row[1]
                    else:
                        plant_extra[row[0]] =rt.replace_abbreviations(row[1])

    elif not query2:
        # Первый запрос для получения bac (связанного Biologicallyactivecompounds)
        bac_query = """
            SELECT DISTINCT ba.bac
            FROM BAC_BiologicalActivity AS ba
            WHERE ba.activity = %s
        """
        with connections['bav'].cursor() as cursor:
            cursor.execute(bac_query, [id])
            bac_ids = [row[0] for row in cursor.fetchall()]

    if query2:
        # reset_q = 'tab_page2' # Очищаем первый поисковый запрос
        query1 = ''
        plant_query, plant_params = qt.get_query('activity_plant_query', query2, id=id)
        # plant_query = """
        # SELECT DISTINCT BAC_Plants.plant
        # FROM BAC_BiologicalActivity AS ba
        #     JOIN
        #     BAC_Plants ON ba.bac = BAC_Plants.bac
        #     LEFT JOIN
        #     Plants ON BAC_Plants.plant = Plants.id
        #     LEFT JOIN
        #     Plants_Names ON BAC_Plants.plant = Plants_Names.plant AND Plants_Names.language=1
        # WHERE ba.activity = %s AND 
        #     (Plants.rus LIKE %s OR Plants.rus LIKE %s OR
        #      LOWER(Plants.eng) LIKE LOWER(%s) OR
        #      LOWER(Plants_Names.name) LIKE LOWER(%s))
        # """
        # with connections['bav'].cursor() as cursor:
        #     cursor.execute(plant_query, [id,
        #                                   '%' + query2 + '%', 
        #                                   '%' + query2.capitalize() + '%', 
        #                                   '%' + query2 + '%',
        #                                   '%' + query2 + '%',
        #                                   ])
        with connections['bav'].cursor() as cursor:
            cursor.execute(plant_query, plant_params)
            plant_ids = [row[0] for row in cursor.fetchall()]
        placeholders = ','.join(['%s'] * len(plant_ids))  # Создаем плейсхолдеры для каждого элемента списка
        bac_query = f"""
            SELECT bba.bac
            FROM BAC_BiologicalActivity as bba
            JOIN BAC_Plants as bp ON bba.bac=bp.bac AND bba.activity = {id}
            WHERE bp.plant IN ({placeholders})
        """
        with connections['bav'].cursor() as cursor:
            cursor.execute(bac_query, plant_ids)
            bac_ids = [row[0] for row in cursor.fetchall()]
            # for row in cursor.fetchall():
            #     bac_ids.append(row[0])
    elif not query1:
        plant_query = """
            SELECT bplants.plant, bplants.extra
            FROM BAC_BiologicalActivity AS ba
            LEFT JOIN BAC_Plants AS bplants ON ba.bac = bplants.bac
            WHERE ba.activity = %s
        """
        with connections['bav'].cursor() as cursor:
            cursor.execute(plant_query, [id])
            # plant_ids = [row[0] for row in cursor.fetchall()]
            for row in cursor.fetchall():
                plant_ids.append(row[0])
                if row[1]:
                    # plant_extra[row[0]] = row[1]
                    if lng_title=='ru':
                        plant_extra[row[0]] = row[1]
                    else:
                        plant_extra[row[0]] =rt.replace_abbreviations(row[1])


    # Запрос объектов Biologicallyactivecompounds по bac_ids
    bac_objects = Biologicallyactivecompounds.objects.using('bav').filter(id__in=bac_ids).order_by('id')

    bac_page_obj, bac_page_obj2, bac_page_number = make_two_pages_for_details(cur_lang, 'bac',
        request, pg_size, bac_objects, 'tab_page2', {})    

    plant_objects = Plants.objects.using('bav').filter(id__in=plant_ids).order_by('id')

    plant_page_obj, plant_page_obj2, plant_page_number = make_two_pages_for_details(cur_lang, 'plant',
        request, pg_size, plant_objects, 'tab_page3', plant_extra)    
    
    bac_query = {
        'name': 'q1',
        'prompt': _('Search compound'),
        'text': query1
    }
    plant_query = {
        'name': 'q2',
        'prompt': _('Search plant'),
        'text': query2
    }

    bac_page = {
        'is_plant': False,
        'active_tab': 'Tab2',
        'cur_page': 'tab_page2',
        'cur_page_num': bac_page_number,
        'other_page': 'tab_page3',
        'other_page_num': plant_page_number,
        'tab_page_obj': bac_page_obj,
        'tab_page_obj2': bac_page_obj2
    }

    plant_page = {
        'is_plant': True,
        'active_tab': 'Tab3',
        'cur_page': 'tab_page3',
        'cur_page_num': plant_page_number,
        'other_page': 'tab_page2',
        'other_page_num': bac_page_number,
        'tab_page_obj': plant_page_obj,
        'tab_page_obj2': plant_page_obj2
    }

    if lng_title=='ru':
        activity_name = activity_item.rus
        tab_captions = ['Описание', 'Соединения' , 'Растения']
    else:
        activity_name = activity_item.eng
        tab_captions = ['Main', 'Compounds' , 'Plants']

    queries = {bac_query['name']: bac_query, plant_query['name']: plant_query}
    pages_data = {bac_page['active_tab']: bac_page, plant_page['active_tab']: plant_page}
    params_str = make_detail_params_str(active_tab, queries, pages_data)
    lng_sel = {'language': lng_title, 'url': 'activity_detail', 'params': params_str, 'id': id}

    return render(request, 'herbalist/activity_detail.html', 
                  {'activity': activity_item, 'activity_name': activity_name,
                   'q1': bac_query, 'q2': plant_query,
                   'tab2': bac_page, 'tab3': plant_page,
                   'active_tab': active_tab,
                   'tab_captions': tab_captions,
                   'active_page': 'activities', 'lng': lng_sel})

def families(request):
    # if request.method == 'POST':
    #     choice = request.POST.get('language', '')
    #     if choice:
    #         context = {'active_page': 'families', 'lang': choice}
    #         return render(request, 'herbalist/index.html', context)
        
    # context = {'active_page': 'families'}
    # return render(request, 'herbalist/index.html', context)
    page_size, links_buttons = get_page_settings(request)
    
    query = request.GET.get('q', '')  # Получаем поисковый запрос из формы
    # family_query = request.GET.get('family', '')  # Получаем поисковый запрос для поиска по family
    # Получение текущей страницы из запроса
    page_number = request.GET.get('page')
    last_page = request.GET.get('last_page', 1)  # Последняя страница перед поиском

    lng_title = get_session_language(request)
    cur_lang = get_object_or_404(Languages.objects.using('bav'), name=lng_title)

    # Если запрос очищен (например, через reset кнопка)
    if request.GET.get('reset'):
        # Если сбрасываем поиск, используем последнюю страницу перед поиском
        page_number = request.GET.get('page1')

    catalog_queryset = Families.objects.using('bav').all().order_by('id')

    # Если есть поисковый запрос, фильтруем объекты по полям eng и rus
    if query:
        if cur_lang.name == 'ru':
            filter = (models.Q(rus__icontains=query) |
                      models.Q(rus__icontains=query.lower()) |
                      models.Q(rus__icontains=query.capitalize()))
        else:
            filter = models.Q(eng__icontains=query)
        catalog_queryset = catalog_queryset.filter(filter)

      # Фильтрация по family (ищем по связанному объекту)
    # if family_query:
    #     plants_queryset = plants_queryset.filter(family__name__icontains=family_query)

    paginator = Paginator(catalog_queryset, page_size)
    catalog_page = paginator.get_page(page_number)

    for page_item in catalog_page:
        if cur_lang.name == 'ru':
            page_item.display_name = page_item.rus
        else:
            page_item.display_name = page_item.eng

    get_params = {
        'q': query,
        'last_page': last_page,
        'page': page_number
    }
    params_str = make_params_str(get_params)
    lng_sel = {'language': lng_title, 'url': 'families', 'params': params_str, 'id': 0}

    return render(request, 'herbalist/families.html', 
                  {'page_obj': catalog_page, 
                   'links_buttons': links_buttons, 'links_buttons_left': -links_buttons, 
                   'query': query, 'last_page': last_page,
                   'active_page': 'families',
                   'lng': lng_sel})

def family_detail(request, id):
    # Получение объекта Plant по id или 404, если объект не найден
    item = get_object_or_404(Families.objects.using('bav'), id=id)

    lng_title = get_session_language(request)
    # cur_lang = get_object_or_404(Languages.objects.using('bav'), name=lng_title)
    # qt = QueryTexts(cur_lang)
    # rt = ReplaceText(cur_lang)

    lng_sel = {'language': lng_title, 'url': 'family_detail', 'params': '?', 'id': id}

    if lng_title == 'ru':
        family_name = item.rus
    else:
        family_name = item.eng

    # Передача объекта plant в шаблон
    return render(request, 'herbalist/family_detail.html', {'family': item, 'family_name': family_name,
                                                            'active_page': 'families', 'lng': lng_sel})

@login_required    
def profile_view(request):
    dynamic_model_choices = [
        ('model_1', 'Model 1'),
        ('model_2', 'Model 2'),
        ('model_3', 'Model 3'),
    ]

    if request.method == 'POST':
        form = UserSettingsForm(request.POST, model_choices=dynamic_model_choices, instance=request.user.settings)
        if form.is_valid():
            form.save()
            # Вы можете добавить сообщение об успешном сохранении или перенаправить пользователя
            messages.success(request, "Settings updated successfully!")
            # return redirect('profile')  # Перенаправление на профиль
            if 'language' in form.changed_data:
                if form.cleaned_data['language'] in dict(settings.LANGUAGES):
                    set_session_language(request, form.cleaned_data['language'])
                    # Активируем выбранный язык
                    # translation.activate(form.cleaned_data['language'])
                    
                    # Сохраняем язык в сессии пользователя
                    # request.session['language'] = form.cleaned_data['language']
                    # request.LANGUAGE_CODE = form.cleaned_data['language']
            return HttpResponseRedirect(reverse('profile'))

        else:
            messages.error(request, 'Failed!')
            return HttpResponseRedirect(reverse('profile'))
    else:
        form = UserSettingsForm(model_choices=dynamic_model_choices, instance=request.user.settings)

    # form = UserSettingsForm(instance=request.user.settings)
    lng_sel = {'language': get_session_language(request), 'url': 'profile', 'params': '?', 'id': 0}
    context = {'settings': request.user.settings, 'form': form, 'lng': lng_sel}
    return render(request, 'registration/profile.html', context=context)

def get_plant_name(plant, cur_lang):
    if cur_lang.name == 'ru':
        return plant.rus
    else:
        first_name = plant.linked_names.filter(language_id=cur_lang.id).first()
        if first_name:
            return first_name.name
        else:
            return plant.eng

@login_required
def mixtures_list(request):
    user = request.user  # Получаем текущего пользователя

    lng_title = get_session_language(request)
    cur_lang = get_object_or_404(Languages.objects.using('bav'), name=lng_title)

    page_size, _ = get_page_settings(request)
    plants_page_size = page_size
    page_size -=2
    if page_size<1:
        page_size=1
    plants_page_size = page_size*2

    cur_mixture = None

    # Удалить растение из текущего сбора
    if request.method == 'POST' and 'delete_plant' in request.POST:
        cur_mixture_id = request.session.get('selected_mixture_id')
        mixture = get_object_or_404(Mixtures, id=cur_mixture_id, user=user)
        plant_id = request.POST.get('delete_plant')
        MixtureList.objects.filter(mixture=mixture, plant_id=plant_id).delete()
        cur_mixture = mixture

    # При выборе сбора (нажатии на ссылку) сохранить его в сессии
    if request.method == 'GET' and 'current_mix' in request.GET:
        cur_mixture_id = request.GET.get('current_mix')
        if cur_mixture_id:
            cur_mixture = get_object_or_404(Mixtures, id=cur_mixture_id, user=user)
            request.session['selected_mixture_id'] = cur_mixture_id

    # Создание нового сбора
    create_mixture = False
    if request.method == 'POST' and 'create_mixture' in request.POST:
        new_mixture_name = request.POST.get('mixture_name')
        if new_mixture_name:
            new_mixture = Mixtures.objects.create(user=user, name=new_mixture_name)
            create_mixture = True
            cur_mixture = new_mixture
            request.session['selected_mixture_id'] = cur_mixture.id

    # Удаление сбора
    if request.method == 'POST' and 'delete_mixture' in request.POST:
        mixture_id = request.POST.get('delete_mixture')
        mixture_to_delete = get_object_or_404(Mixtures, id=mixture_id, user=user)
        mixture_to_delete.delete()

    # Получаем параметр plant_id, если он передан
    plant_id = request.GET.get('plant_id')
    if plant_id=='None':
        plant_id=None
    plant = None
    if plant_id:
        plant = get_object_or_404(Plants.objects.using('bav'), id=plant_id)
        request.session['selected_plant_id'] = plant.id  # Сохраняем plant в сессии
    else:
        request.session['selected_plant_id'] = None

    if request.method == 'POST' and 'clear_curent_plant' in request.POST:
        plant = None
        request.session['selected_plant_id'] = None
        plant_id=None
    
    plant_name =''
    if plant:
        plant_name = get_plant_name(plant, cur_lang)

    # Получаем сбор, если пользователь выбрал его из списка
    # if request.method == "POST" and 'mixture_id' in request.POST:
    #     mixture_id = request.POST.get('mixture_id')
    if request.method == "GET" and 'mixture_id' in request.GET:
        mixture_id = request.GET.get('mixture_id')
        mixture = get_object_or_404(Mixtures, id=mixture_id, user=user)

        # Проверяем, есть ли plant_id в сессии
        selected_plant_id = request.session.get('selected_plant_id')
        if selected_plant_id:
            # plant = get_object_or_404(Plants.objects.using('bav'), id=selected_plant_id)

            # Проверяем, есть ли уже такая запись в MixtureList
            if not MixtureList.objects.filter(mixture=mixture, plant_id=selected_plant_id).exists():
                MixtureList.objects.create(mixture=mixture, plant_id=selected_plant_id)
                # messages.success(request, f"Растение '{plant_id}' добавлено в сбор '{mixture.name}'.")
            else:
                messages.info(request, f"Plant '{plant.name}' already exists in '{mixture.name}' collection.")
            # Удаляем plant_id из сессии
        request.session['selected_mixture_id'] = mixture_id
        cur_mixture = mixture

    # Получаем все смеси текущего пользователя
    mixtures = Mixtures.objects.filter(user=user).order_by('id')

    paginator = Paginator(mixtures, page_size)
    if create_mixture:
        page_number = paginator.num_pages
    else:
        page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    if not cur_mixture:
        for mixture_item in page_obj:
            cur_mixture = mixture_item
            request.session['selected_mixture_id'] = cur_mixture.id
            break
        
    plants_page_obj=odd_items=even_items=plants_page_number=None
    max_len = ''
    if cur_mixture:
        mixture_plants = MixtureList.objects.filter(mixture=cur_mixture).order_by('id')
        plants_paginator = Paginator(mixture_plants, plants_page_size)  # Пагинация для списка растений
        plants_page_number = request.GET.get('plants_page')
        plants_page_obj = plants_paginator.get_page(plants_page_number)
        for item in plants_page_obj:
            plant2 = Plants.objects.using('bav').get(id=item.plant_id)
            # mixture_item.plants.append(plant)
            item.plant = plant2
            item.plant.display_name = get_plant_name(plant2, cur_lang)
        even_items = plants_page_obj[::2]
        odd_items = plants_page_obj[1::2]
        max_len = max(len(even_items), len(odd_items))
     

    get_params = {
        'current_mix': '' if not cur_mixture else cur_mixture.id,
        'plant_id': plant_id,
        'plants_page': plants_page_number,
        'page': page_number
    }
    params_str = make_params_str(get_params)
    lng_sel = {'language': lng_title, 'url': 'mixtures_list', 'params': params_str, 'id': 0}

    return render(request, 'herbalist/mixtures.html', {
        'page_obj': page_obj, 'plant': plant, 'plant_id': plant_id, 'plant_name': plant_name,
        'cur_mixture': cur_mixture,
        'plants_page_obj': plants_page_obj,
        'even_items': even_items, 'odd_items': odd_items, 'max_len': max_len,
        'lng': lng_sel
    })

@login_required
def mixture_detail(request, id):
    page_size, links_buttons = get_page_settings(request)
    pg_size = page_size - 2

    user = request.user  # Получаем текущего пользователя
    mixture = get_object_or_404(Mixtures, id=id, user=user)
    # mixture_list_items = MixtureList.objects.filter(mixture=mixture)
    # for item in mixture_list_items:
    #     print(f'plant_id: {item.plant_id}')
    
    lng_title = get_session_language(request)
    cur_lang = get_object_or_404(Languages.objects.using('bav'), name=lng_title)
    qt = QueryTexts(cur_lang)
    rt = ReplaceText(cur_lang)

    selected_id = request.GET.get('sel_id')
    if selected_id:
        mixture_list_entry = MixtureList.objects.filter(mixture=mixture, plant_id=selected_id).first()
        # Проверяем, что запись найдена, и меняем значение selected
        if mixture_list_entry:
            mixture_list_entry.selected = not mixture_list_entry.selected
            mixture_list_entry.save()
    # change_mixture_selection(user, selected_id)

    to_delete_id = request.GET.get('del_id')
    if to_delete_id:
        MixtureList.objects.filter(mixture=mixture, plant_id=to_delete_id).delete()
        # delete_from_mixture(user, selected_id)

    active_tab = request.GET.get('active_tab', 'Tab1')  # 'Main' по умолчанию, если параметр отсутствует

    query1 = request.GET.get('q1', '')  # Получаем поисковый запрос из формы
    query2 = request.GET.get('q2', '')  # Получаем поисковый запрос для поиска
    query3 = request.GET.get('q3', '')  # Получаем поисковый запрос для поиска

    reset_q = request.GET.get('reset_q')
    if reset_q == 'tab_page2':
        query1=''
    if reset_q == 'tab_page3':
        query2=''
    if reset_q == 'tab_page1':
        query3=''

    my_q = request.GET.get('my_q', '')  # Где введен поисковый запрос: на закладке Tab2 или Tab3
    if my_q == 'q1':
        query2 = ''
    elif my_q == 'q2':
        query1 = ''

    mixture_plants = MixtureList.objects.filter(mixture=mixture).order_by('id')
    selected_plants = MixtureList.objects.filter(mixture=mixture, selected=True).order_by('id')

    plant_ids = []
    plant_extra = dict()
    plant_page_obj, plant_page_obj2, plant_page_number = make_two_mixture_pages_for_details(cur_lang, 
        request, pg_size, mixture_plants, 'tab_page1', plant_extra, search_text=query3)    

    bac_ids = []
    bac_extra = dict()
    activity_ids = []
    activity_extra_data = []
    activity_extra = dict()

    selected_plants_list = [plant.plant_id for plant in selected_plants]
    selected_ph = ','.join(['%s'] * len(selected_plants_list))  # Создаем плейсхолдеры для каждого элемента списка
    query1_like = '%' + query1 + '%'
    query1_like_cap = '%' + query1.capitalize() + '%'
    query1_like_low = '%' + query1.lower() + '%'
    query2_like = '%' + query2 + '%'
    query2_like_cap = '%' + query2.capitalize() + '%'
    query2_like_low = '%' + query2.lower() + '%'
    if query2:
        bac_query = f"""
            SELECT bp.bac
            FROM BAC_Plants AS bp
                LEFT JOIN
                BiologicallyActiveCompounds AS bc ON bc.id = bp.bac
            WHERE plant IN ({selected_ph}) AND 
                (bc.rus LIKE %s OR bc.rus LIKE %s OR 
                    LOWER(bc.eng) LIKE %s );
        """
        with connections['bav'].cursor() as cursor:
            cursor.execute(bac_query, selected_plants_list+[query2_like, query2_like_cap, query2_like_low])
            for row in cursor.fetchall():
                bac_ids.append(row[0])
                # bac_extra[row[0]] = row[1]
        placeholders = ','.join(['%s'] * len(bac_ids))  # Создаем плейсхолдеры для каждого элемента списка
        activity_query = f"""
            SELECT DISTINCT BAC_BiologicalActivity.activity, text
            FROM BAC_Plants
            JOIN BAC_BiologicalActivity ON BAC_Plants.bac = BAC_BiologicalActivity.bac AND BAC_Plants.plant IN ({selected_ph})
            WHERE BAC_BiologicalActivity.bac IN({placeholders})
        """
        with connections['bav'].cursor() as cursor:
            cursor.execute(activity_query, selected_plants_list+bac_ids)
            for row in cursor.fetchall():
                activity_ids.append(row[0])
                activity_extra[row[0]]=row[1]
    elif not query1:
        # Первый запрос для получения bac (связанного Biologicallyactivecompounds)
        bac_query = f"""
            SELECT bac
            FROM BAC_Plants
            WHERE plant IN ({selected_ph})
        """
        with connections['bav'].cursor() as cursor:
            cursor.execute(bac_query, selected_plants_list)
            # bac_ids = [row[0] for row in cursor.fetchall()]
            for row in cursor.fetchall():
                bac_ids.append(row[0])
                # bac_extra[row[0]] = row[1]

    if query1:
        activity_query = f"""
            SELECT DISTINCT ba.activity, ba.text
            FROM BAC_Plants AS bp
                JOIN
                BAC_BiologicalActivity AS ba ON bp.bac = ba.bac
                JOIN
                BiologicalActivity AS ba2 ON ba.activity = ba2.id
            WHERE bp.plant IN ({selected_ph}) AND (ba2.rus LIKE %s OR ba2.rus LIKE %s OR LOWER(ba2.eng) LIKE %s);
        """
        with connections['bav'].cursor() as cursor:
            cursor.execute(activity_query, selected_plants_list+[query1_like, query1_like_cap, query1_like_low])
            for row in cursor.fetchall():
                activity_ids.append(row[0])
                activity_extra[row[0]]=row[1]
        placeholders = ','.join(['%s'] * len(activity_ids))  # Создаем плейсхолдеры для каждого элемента списка
        bac_query = f"""
            SELECT bp.bac
            FROM BAC_Plants as bp
            JOIN BAC_BiologicalActivity as ba ON ba.bac=bp.bac AND bp.plant IN ({selected_ph})
            WHERE ba.activity IN ({placeholders})
        """
        with connections['bav'].cursor() as cursor:
            cursor.execute(bac_query, selected_plants_list+activity_ids)
            # bac_ids = [row[0] for row in cursor.fetchall()]
            for row in cursor.fetchall():
                bac_ids.append(row[0])
                # bac_extra[row[0]] = row[1]
    elif not query2:
        activity_query = f"""
            SELECT DISTINCT BAC_BiologicalActivity.activity, text
            FROM BAC_Plants
            LEFT JOIN BAC_BiologicalActivity ON BAC_Plants.bac = BAC_BiologicalActivity.bac
            WHERE BAC_Plants.plant IN ({selected_ph}) AND BAC_BiologicalActivity.activity IS NOT NULL
        """
        with connections['bav'].cursor() as cursor:
            cursor.execute(activity_query, selected_plants_list)
            for row in cursor.fetchall():
                activity_ids.append(row[0])
                activity_extra[row[0]]=row[1]


    # Запрос объектов Biologicallyactivecompounds по bac_ids
    bac_objects = Biologicallyactivecompounds.objects.using('bav').filter(id__in=bac_ids).order_by('id')

    bac_page_obj, bac_page_obj2, bac_page_number = make_two_pages_for_details(cur_lang, 'bac',
        request, pg_size, bac_objects, 'tab_page3', bac_extra)    

    activity_objects = Biologicalactivity.objects.using('bav').filter(id__in=activity_ids).order_by('id')

    activity_page_obj, activity_page_obj2, activity_page_number = make_two_pages_for_details(cur_lang, 'activity',
        request, pg_size, activity_objects, 'tab_page2', activity_extra, True)

    activity_query = {
        'name': 'q1',
        'prompt': _('Search activity'),
        'text': query1
    }
    bac_query = {
        'name': 'q2',
        'prompt': _('Search compound'),
        'text': query2
    }
    plant_query = {
        'name': 'q3',
        'prompt': _('Search plant'),
        'text': query3
    }

    activity_page = {
        'is_plant': False,
        'active_tab': 'Tab2',
        'cur_page': 'tab_page2',
        'cur_page_num': activity_page_number,
        'other_page': 'tab_page3',
        'other_page_num': bac_page_number,
        'third_page': 'tab_page1',
        'third_page_num': plant_page_number,
        'tab_page_obj': activity_page_obj,
        'tab_page_obj2': activity_page_obj2
    }

    bac_page = {
        'is_plant': False,
        'active_tab': 'Tab3',
        'cur_page': 'tab_page3',
        'cur_page_num': bac_page_number,
        'other_page': 'tab_page2',
        'other_page_num': activity_page_number,
        'third_page': 'tab_page1',
        'third_page_num': plant_page_number,
        'tab_page_obj': bac_page_obj,
        'tab_page_obj2': bac_page_obj2
    }

    plant_page = {
        'is_plant': True,
        'active_tab': 'Tab1',
        'cur_page': 'tab_page1',
        'cur_page_num': plant_page_number,
        'other_page': 'tab_page2',
        'other_page_num': activity_page_number,
        'third_page': 'tab_page3',
        'third_page_num': bac_page_number,
        'tab_page_obj': plant_page_obj,
        'tab_page_obj2': plant_page_obj2
    }

    # get_params = {
    #     'current_mix': cur_mixture.id,
    #     'plant_id': plant_id,
    #     'plants_page': plants_page_number,
    #     'page': page_number
    # }
    queries = {activity_query['name']: activity_query, bac_query['name']: bac_query, plant_query['name']: plant_query}
    pages_data = {activity_page['active_tab']:activity_page, bac_page['active_tab']: bac_page, plant_page['active_tab']: plant_page}
    params_str = make_detail_params_str(active_tab, queries, pages_data)
    lng_sel = {'language': lng_title, 'url': 'mixture_detail', 'params': params_str, 'id': id}

    if lng_title == 'ru':
        tab_captions = ['Растения', 'Активность' , 'Соединения']
    else:
        tab_captions = ['Plants', 'Activities' , 'Compounds']

    return render(request, 'herbalist/mixture_detail.html', 
                  {'q1': activity_query, 'q2': bac_query, 'q3': plant_query,
                   'tab2': activity_page, 'tab3': bac_page, 'tab1': plant_page,
                   'active_tab': active_tab,
                   'tab_captions': tab_captions,
                   'mixture_name': mixture.name, 'lng': lng_sel
                   })    