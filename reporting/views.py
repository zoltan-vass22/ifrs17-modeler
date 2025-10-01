from django.http import Http404
from django.shortcuts import render
from results.models import ResultSet, RollforwardLine
from itertools import groupby

def run_list(request):
    runs = ResultSet.objects.select_related("group", "group__portfolio", "group__product")\
                            .order_by("-created_at")[:50]
    return render(request, "reporting/run_list.html", {"runs": runs})

def run_detail(request, result_id: int):
    try:
        rs = ResultSet.objects.select_related("group", "group__portfolio", "group__product").get(pk=result_id)
    except ResultSet.DoesNotExist:
        raise Http404("ResultSet not found")
    lines = RollforwardLine.objects.filter(result=rs).order_by("period_index", "movement_type", "component")
    # group in Python by period
    period_groups = []
    for period, group in groupby(lines, key=lambda x: x.period_index):
        g = list(group)
        period_groups.append((period, g))
    return render(request, "reporting/run_detail.html", {"rs": rs, "period_groups": period_groups})
