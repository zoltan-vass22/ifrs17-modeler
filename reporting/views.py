from django.http import Http404
from django.shortcuts import render
from results.models import ResultSet, RollforwardLine

def run_list(request):
    runs = ResultSet.objects.select_related("group", "group__portfolio", "group__product")\
                            .order_by("-created_at")[:50]
    return render(request, "reporting/run_list.html", {"runs": runs})

def run_detail(request, result_id: int):
    try:
        rs = ResultSet.objects.select_related("group", "group__portfolio", "group__product").get(pk=result_id)
    except ResultSet.DoesNotExist:
        raise Http404("ResultSet not found")
    lines = RollforwardLine.objects.filter(result=rs).order_by("period_index", "component")
    return render(request, "reporting/run_detail.html", {"rs": rs, "lines": lines})
