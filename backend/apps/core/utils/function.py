# ประกาศ Function กลาง
from datetime import datetime
from django.db import  models
from django.db.models import Q, ManyToManyField, DateField, DateTimeField, Func, Value
from querystring_parser import parser
from rest_framework.generics import ListAPIView
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated

import socket
from django.utils import timezone
from apps.core.model.authorize.models import UserLog
import traceback
from user_agents import parse

cached_keys = []

def auto_slug():
    return datetime.now().strftime('%Y%m%d%H%M%S%f')

def to_dict(self):
    opts = self._meta
    data = {}
    for f in opts.concrete_fields + opts.many_to_many:
        if isinstance(f, ManyToManyField):
            if self.pk is None:
                data[f.name] = []
            else:
                related_objects = f.value_from_object(self)
                if isinstance(related_objects, list):
                    data[f.name] = [obj.pk for obj in related_objects]
                else:
                    data[f.name] = list(related_objects.values_list('pk', flat=True))
        elif isinstance(f, DateField) and not isinstance(f, DateTimeField):
            if f.value_from_object(self) is not None:
                data[f.name] = f.value_from_object(self).strftime('%d/%m/%Y')
        else:
            data[f.name] = f.value_from_object(self)
    return data

def to_list(object):
    list_data = list()
    for foo in object:
        list_data.append(to_dict(foo))
    return list_data

class StandardResultsSetPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'pageSize'
    max_page_size = 9999

class BaseModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True

    @classmethod
    def from_db(cls, db, field_names, values):  # เก็บข้อมูลก่อนแก้ไข old values
        instance = super().from_db(db, field_names, values)
        instance._state.adding = False
        instance._state.db = db
        instance._old_values = dict(zip(field_names, values))
        return instance

    def data_changed(self):  # เช็ค old values กับ new values
        fields = list()
        if hasattr(self, '_old_values'):
            opts = self._meta
            if not self.pk or not self._old_values:
                return fields
            for field in opts.concrete_fields + opts.many_to_many:
                if isinstance(field, ManyToManyField):
                    old_value = set(self._old_values.get(field.name, []))
                    new_value = set(getattr(self, field.name).all())
                    if old_value != new_value:
                        fields.append(str(field.verbose_name))
                else:
                    if getattr(self, field.column) != self._old_values[field.column]:
                        fields.append(str(field.verbose_name))
            return fields
        return fields

class BaseListAPIView(ListAPIView):
    permission_classes = (IsAuthenticated,)
    pagination_class = StandardResultsSetPagination
    serializer_class = None
    queryset = None

    def _build_filters(self, filters, django_filters, filter_logic):
        for filter_id in filters:
            filter = filters[filter_id]
            my_filter = dict()
            if ('field' in filter) and ('operator' in filter) and ('value' in filter):
                if filter['operator'] == 'startswith' or filter['operator'] == 'endswith' or \
                        filter['operator'] == 'contains':
                    filter['operator'] = 'i' + filter['operator']
                if filter['field'] == 'status_name':
                    filter['field'] = 'status'
                if "." in filter['field']:
                    filter['field'] = filter['field'].replace('.', '__')
                    # my_filter[filter['field']] = filter['value']
                if (filter['value'] == 'true' or filter['value'] == 'false') and filter_logic == 'AND':
                    if filter['operator'] == 'eq':
                        if filter['value'] == 'true':
                            my_filter[filter['field']] = True
                        else:
                            my_filter[filter['field']] = False
                    else:
                        if filter['value'] == 'true':
                            my_filter[filter['field'] + '__' + filter['operator']] = True
                        else:
                            my_filter[filter['field'] + '__' + filter['operator']] = False
                elif (filter['value'] == 'true' or filter['value'] == 'false') and filter_logic == 'OR':
                    my_filter = dict()
                else:
                    if filter['operator'] == 'eq':
                        my_filter[filter['field']] = filter['value']
                    else:
                        my_filter[filter['field'] + '__' + filter['operator']] = filter['value']
            if my_filter:
                django_filters.append(my_filter)
        return django_filters

    def _build_sorts(self, sorts, django_sorts):
        for sort_id in sorts:
            sort = sorts[sort_id]
            if "." in sort['field']:
                sort['field'] = sort['field'].replace('.', '__')
            if ('field' in sort) and ('dir' in sort):
                if sort['dir'].lower() == 'desc':
                    django_sorts.append('-%s' % sort['field'])
                else:
                    django_sorts.append(sort['field'])
        if (len(django_sorts) == 0):
            django_sorts.append('id')
        return django_sorts

    def get_queryset(self, *args, **kwargs):
        arguments = parser.parse(self.request.GET.urlencode())
        # print(arguments)
        filter_arg = list()
        sort_arg = list()
        filter_logic = 'and'
        items = self.queryset
        first_filter = {}
        for key, value in arguments.items():
            if key not in ['take', 'skip', 'page', 'pageSize', 'sort', 'filter']:
                if isinstance(value, dict):
                    for key2, value2 in value.items():
                        first_filter[key + '__' + key2] = value2
                else:
                    first_filter[key] = value
        if first_filter:
            items = items.filter(**first_filter)
        # if "status" in arguments:
        #     items = items.filter(status=arguments['status'])
        if ("filter" in arguments) and ('filters' in arguments['filter']):
            filter_logic = arguments['filter']['logic'].upper()
            filter_arg = self._build_filters(arguments['filter']['filters'], filter_arg, filter_logic)
        if 'sort' in arguments:
            sort_arg = self._build_sorts(arguments['sort'], sort_arg)
        else:
            sort_arg = ['id']
        # filter and sort
        my_filter_qs = Q()
        for creator_filter in filter_arg:
            filters = Q(**creator_filter)
            my_filter_qs.add(filters, filter_logic)
        # print(my_filter_qs)
        if len(sort_arg) > 0:
            items = items.filter(my_filter_qs).order_by(*sort_arg)
        return items

class EnableBackwardIterator:
    def __init__(self, iterator):
        self.iterator = iterator
        self.history = [None, ]
        self.i = 0

    def next(self):
        self.i += 1
        if self.i < len(self.history):
            return self.history[self.i]
        else:
            elem = next(self.iterator, None)
            if elem:
                self.history.append(elem)
            return elem

    def prev(self):
        self.i -= 1
        if self.i == 0:
            raise StopIteration
        else:
            return self.history[self.i]

def get_user_os_browser_architecture(request):
    user_agent_str = request.META.get('HTTP_USER_AGENT', '')
    user_agent = parse(user_agent_str)

    # OS และเวอร์ชัน
    os_name = user_agent.os.family or "Unknown OS"
    os_version = user_agent.os.version_string or ""

    # Architecture (32-bit หรือ 64-bit)
    architecture = "Unknown"
    if "WOW64" in user_agent_str or "Win64" in user_agent_str or "x64" in user_agent_str:
        architecture = "64-bit"
    elif "Win32" in user_agent_str or "x86" in user_agent_str:
        architecture = "32-bit"

    # Browser และเวอร์ชัน
    browser_name = user_agent.browser.family or "Unknown Browser"
    browser_version = user_agent.browser.version_string or ""

    os_full = f"{os_name} {os_version} {architecture}".strip()
    browser_full = f"{browser_name} {browser_version}".strip()

    return {
        "os": os_full,
        "browser": browser_full
    }

def get_client_ip(request):
    """
    Extract client IP from Django request considering common proxy headers.
    Returns 'unknown' when not available.
    """
    if not request:
        return "unknown"
    # Prefer common real-ip headers set by reverse proxies
    headers_to_check = [
        'HTTP_X_REAL_IP',
        'HTTP_X_CLIENT_IP',
        'HTTP_CLIENT_IP',
        'HTTP_CF_CONNECTING_IP',
        'HTTP_X_FORWARDED_FOR',
    ]
    for h in headers_to_check:
        val = request.META.get(h)
        if val:
            # X-Forwarded-For may contain a list of IPs
            if h == 'HTTP_X_FORWARDED_FOR':
                return val.split(',')[0].strip()
            return val.strip()
    return request.META.get('REMOTE_ADDR', 'unknown')

def create_user_log(
    user=None,
    action="",
    detail="",
    status="",
    request=None,
    audiofile_id=None,
    exception=None,       # 👈 เพิ่มพารามิเตอร์สำหรับเก็บ error object
):
    """
    ฟังก์ชันกลางสำหรับสร้าง log การใช้งานระบบ (รองรับทั้ง success และ error)

    Parameters:
        user (User|None): ผู้ใช้งาน (อาจเป็น None ได้)
        action (str): ประเภทของ action เช่น "Login", "Create Config Group", "Delete Record"
        detail (str): รายละเอียดเพิ่มเติม
        status (str): สถานะ เช่น "success", "error"
        request (HttpRequest|None): สำหรับดึงข้อมูล IP, Browser, OS
        audiofile_id (int|None): อ้างอิงไฟล์เสียง (optional)
        exception (Exception|None): ถ้ามี error จะถูกบันทึกข้อความอัตโนมัติ
    """

    # ดึงข้อมูล client OS / browser
    try:
        info = get_user_os_browser_architecture(request) if request else {"os": "-", "browser": "-"}
    except Exception:
        info = {"os": "-", "browser": "-"}

    # ดึง IP ของ client (จาก request)
    try:
        client_ip = get_client_ip(request)
    except Exception:
        client_ip = "unknown"

    # ถ้ามี Exception ให้แนบ traceback ด้วย
    if exception is not None:
        tb = traceback.format_exc()
        detail = f"{detail}\nException: {str(exception)}\nTraceback:\n{tb}"
        status = "error"

    # พยายามบันทึก log ลงฐานข้อมูล
    try:
        UserLog.objects.create(
            user=user,
            action=action,
            timestamp=timezone.now(),
            detail=detail,
            ip_address=client_ip,
            # audiofile_id=audiofile_id,
            client_type=f"{info['os']} / {info['browser']}",
            status=status,
        )
        
        print('timezone:', timezone.now())
    except Exception as log_error:
        # ถ้าแม้แต่การเขียน log เองยัง error จะ print ออก console เพื่อไม่ให้ระบบล่ม
        print(f"[UserLog ERROR] Failed to write log: {log_error}")
        print(f"Original log detail: {detail}")