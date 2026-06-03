from rest_framework.response import Response

from rest_api.models import Flat

from rest_framework.views import APIView
from django.db.models import Avg, Min, Max, Sum

class FlatAPIView(APIView):
    def get(self, request):
        queryset = Flat.objects.all().values()
        params = request.query_params
        price_per_m2_coeff_user = 3
        common_ecology_coeff_user = 3
        population_density_coeff_user = 3
        green_spaces_coeff_user = 3
        negative_impact_coeff_user = 3
        phone_nets_coeff_user = 3
        crime_coeff_user = 3
        try:
            for param in params:
                if param == "min_price":
                    queryset = queryset.filter(price_per_month__gte=params[param])
                elif param == "max_price":
                    queryset = queryset.filter(price_per_month__lte=params[param])
                elif param == "time_to_underground_under":
                    queryset = queryset.filter(time_to_underground__lte=params[param])
                elif param == "rooms":
                    queryset = queryset.filter(rooms=params[param])
                elif param == "region":
                    queryset = queryset.filter(region=params[param])
                elif param == "district":
                    queryset = queryset.filter(district=params[param])
                elif param == "underground":
                    queryset = queryset.filter(underground=params[param])
                elif param == "price_per_m2_coeff":
                    price_per_m2_coeff_user = int(params[param])
                elif param == "common_ecology_coeff":
                    common_ecology_coeff_user = int(params[param])
                elif param == "population_density_coeff":
                    population_density_coeff_user = int(params[param])
                elif param == "green_spaces_coeff":
                    green_spaces_coeff_user = int(params[param])
                elif param == "negative_impact_coeff":
                    negative_impact_coeff_user = int(params[param])
                elif param == "phone_nets_coeff":
                    phone_nets_coeff_user = int(params[param])
                elif param == "crime_coeff":
                    crime_coeff_user = int(params[param])
                else:
                    return Response("Wrong parameters", status=400)
        except(ValueError):
            return Response("Wrong parameter value", status=400)
        if(queryset.count() == 0):
            return Response("No flats found", status=200)
        min_price = queryset.aggregate(Min('price_per_m2'))['price_per_m2__min']
        max_price = queryset.aggregate(Max('price_per_m2'))['price_per_m2__max']
        difference = max_price - min_price
        flatlist = list(queryset)
        for flat in flatlist:
            price_per_m2_score = (10. - round((flat['price_per_m2'] - min_price)/(0.0000001 + difference / 10.), 2)) * price_per_m2_coeff_user
            flat["price_per_m2_score"] = price_per_m2_score
            common_ecology_score = round(flat['common_ecology_coeff'] * common_ecology_coeff_user, 2)
            flat["common_ecology_score"] = common_ecology_score
            population_density_score = round(flat['population_density_coeff'] * population_density_coeff_user, 2)
            flat["population_density_score"] = population_density_score
            green_spaces_score = round(flat['green_spaces_coeff'] * green_spaces_coeff_user, 2)
            flat["green_spaces_score"] = green_spaces_score
            negative_impact_score = round(flat['negative_impact_coeff'] * negative_impact_coeff_user, 2)
            flat["negative_impact_score"] = negative_impact_score
            phone_nets_score = round(flat['phone_nets_coeff'] * phone_nets_coeff_user, 2)
            flat["phone_nets_score"] = phone_nets_score
            crime_score = round(flat['crime_coeff'] * crime_coeff_user, 2)
            flat["crime_score"] = crime_score
            flat['score'] = round(price_per_m2_score + common_ecology_score + population_density_score + green_spaces_score + negative_impact_score + phone_nets_score + crime_score, 2)
        flatlist.sort(key=lambda flat: flat["score"], reverse=True)
        return Response(flatlist)


from django.http import JsonResponse
from django.db.models import Avg, Min, Max, Count, Q, F


def market_stats(request):
    flats = Flat.objects.all()

    rooms_dist = {}
    for r in [1, 2, 3]:
        count = flats.filter(rooms=r).count()
        if count > 0:
            rooms_dist[f'{r}_комн'] = count

    stats = {
        'total_flats': flats.count(),
        'price': {
            'avg': round(flats.aggregate(Avg('price_per_month'))['price_per_month__avg'] or 0, 2),
            'min': flats.aggregate(Min('price_per_month'))['price_per_month__min'] or 0,
            'max': flats.aggregate(Max('price_per_month'))['price_per_month__max'] or 0,
        },
        'area': {
            'avg': round(flats.aggregate(Avg('total_meters'))['total_meters__avg'] or 0, 2),
            'min': flats.aggregate(Min('total_meters'))['total_meters__min'] or 0,
            'max': flats.aggregate(Max('total_meters'))['total_meters__max'] or 0,
        },
        'rooms_distribution': rooms_dist,
        'top_districts': list(flats.values('district')
                              .annotate(avg_price=Avg('price_per_month'))
                              .order_by('-avg_price')[:5]),
    }
    return JsonResponse(stats, safe=False)


def price_by_district(request):
    data = list(Flat.objects.values('district')
                .annotate(
        avg_price=Avg('price_per_month'),
        avg_price_per_m2=Avg('price_per_m2'),
        count=Count('id')
    )
                .order_by('-avg_price'))
    return JsonResponse(data, safe=False)


def price_histogram(request):
    """Гистограмма распределения цен"""
    flats = Flat.objects.all()

    bins = [0, 30000, 50000, 70000, 100000, 150000, 200000, 300000]
    labels = ['0-30k', '30-50k', '50-70k', '70-100k', '100-150k', '150-200k', '200k+']

    histogram = []
    for i in range(len(bins) - 1):
        count = flats.filter(
            price_per_month__gte=bins[i],
            price_per_month__lt=bins[i + 1]
        ).count()
        histogram.append({
            'range': labels[i],
            'count': count,
            'min': bins[i],
            'max': bins[i + 1]
        })

    return JsonResponse({'histogram': histogram, 'total': flats.count()})


def correlation_analysis(request):
    """Корреляция цены с факторами"""
    flats = Flat.objects.all()

    first_floors = flats.filter(floor=1).aggregate(Avg('price_per_month'))['price_per_month__avg']
    last_floors = flats.filter(floor=F('floors_count')).aggregate(Avg('price_per_month'))['price_per_month__avg']
    middle_floors = flats.exclude(floor=1).exclude(floor=F('floors_count')).aggregate(Avg('price_per_month'))[
        'price_per_month__avg']

    high_ecology = flats.filter(common_ecology_coeff__gte=7).aggregate(Avg('price_per_month'))['price_per_month__avg']
    low_ecology = flats.filter(common_ecology_coeff__lte=4).aggregate(Avg('price_per_month'))['price_per_month__avg']

    analysis = {
        'price_by_floor': {
            'first_floor': round(first_floors or 0, 2),
            'middle_floors': round(middle_floors or 0, 2),
            'last_floor': round(last_floors or 0, 2),
        },
        'price_by_ecology': {
            'high_ecology_areas': round(high_ecology or 0, 2),
            'low_ecology_areas': round(low_ecology or 0, 2),
        },
        'price_per_m2_by_district': list(flats.values('district')
                                         .annotate(avg_price_per_m2=Avg('price_per_m2'))
                                         .order_by('-avg_price_per_m2')[:10]),
    }
    return JsonResponse(analysis, safe=False)