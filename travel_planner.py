from typing import Dict, List, Optional
import re

from enhanced_knowledge import ENHANCED_CITY_DATA as DETAILED_CITY_DATA


class TravelPlanner:
    def __init__(self):
        self.detailed_city_data = DETAILED_CITY_DATA
        self.city_pattern = re.compile(r'(' + '|'.join(DETAILED_CITY_DATA.keys()) + r')', re.IGNORECASE)
        self.season_pattern = re.compile(r'春|夏|秋|冬|寒假|暑假|春节|国庆', re.IGNORECASE)
        self.days_pattern = re.compile(r'(\d+)天')
        self.budget_pattern = re.compile(r'预算(\d+(?:[.,]\d+)?)[万]?')
        self.from_pattern = re.compile(r'(从|在)(.+?)去')
        
        self.season_cities = {
            "春季": ["杭州", "苏州", "扬州", "无锡", "桂林"],
            "夏季": ["青岛", "大连", "威海", "承德", "贵阳"],
            "秋季": ["北京", "西安", "南京", "长沙", "成都"],
            "冬季": ["三亚", "海口", "西双版纳", "昆明", "哈尔滨"]
        }
        
        self.budget_levels = {
            '经济型': {'min': 0, 'max': 2000, 'days': 2},
            '舒适型': {'min': 2000, 'max': 5000, 'days': 3},
            '豪华型': {'min': 5000, 'max': 10000, 'days': 5},
            '奢华型': {'min': 10000, 'max': float('inf'), 'days': 5}
        }

        self.train_routes = {
            ("北京", "三亚"): {"price": 1200, "duration": "35小时", "train": "Z501"},
            ("北京", "上海"): {"price": 553, "duration": "4.5小时", "train": "G101"},
            ("北京", "杭州"): {"price": 649, "duration": "5.5小时", "train": "G171"},
            ("北京", "成都"): {"price": 864, "duration": "8小时", "train": "G87"},
            ("北京", "西安"): {"price": 515, "duration": "4.5小时", "train": "G877"},
            ("上海", "杭州"): {"price": 73, "duration": "1小时", "train": "G7501"},
            ("上海", "苏州"): {"price": 34, "duration": "25分钟", "train": "G7001"},
            ("成都", "西安"): {"price": 263, "duration": "3.5小时", "train": "G88"},
            ("广州", "三亚"): {"price": 456, "duration": "11小时", "train": "Z8001"},
            ("广州", "桂林"): {"price": 175, "duration": "2.5小时", "train": "G2901"},
            ("深圳", "三亚"): {"price": 502, "duration": "12小时", "train": "Z201"},
            ("西安", "成都"): {"price": 263, "duration": "3.5小时", "train": "G88"},
            ("杭州", "苏州"): {"price": 63, "duration": "1小时", "train": "G7301"},
            ("成都", "重庆"): {"price": 96, "duration": "1.5小时", "train": "G8601"},
            ("长沙", "桂林"): {"price": 171, "duration": "2.5小时", "train": "G431"},
            ("青岛", "北京"): {"price": 335, "duration": "3.5小时", "train": "G2"},
            ("哈尔滨", "北京"): {"price": 540, "duration": "6小时", "train": "G1202"},
            ("苏州", "南京"): {"price": 84, "duration": "1.5小时", "train": "G7005"},
            ("桂林", "阳朔"): {"price": 20, "duration": "1小时", "train": "D8401"},
            ("张家界", "长沙"): {"price": 120, "duration": "2小时", "train": "G6401"}
        }

    def extract_city(self, query: str) -> Optional[str]:
        to_pattern = re.compile(r'去(.+?)(旅游|玩|旅行|吧|。|，|$)')
        to_match = to_pattern.search(query)
        if to_match:
            to_city = to_match.group(1).strip()
            for city in DETAILED_CITY_DATA.keys():
                if city in to_city:
                    return city
        
        match = self.city_pattern.search(query)
        return match.group(1) if match else None

    def extract_season(self, query: str) -> Optional[str]:
        if '寒假' in query or '春节' in query:
            return '冬季'
        if '暑假' in query:
            return '夏季'
        if '国庆' in query:
            return '秋季'
        
        match = self.season_pattern.search(query)
        if match:
            text = match.group()
            season_map = {'春': '春季', '夏': '夏季', '秋': '秋季', '冬': '冬季'}
            if text in season_map:
                return season_map[text]
        return None

    def extract_days(self, query: str) -> Optional[int]:
        match = self.days_pattern.search(query)
        return int(match.group(1)) if match else None

    def extract_budget(self, query: str) -> Optional[float]:
        match = self.budget_pattern.search(query)
        if match:
            value = float(match.group(1))
            if '万' in match.group():
                return value * 10000
            return value
        return None

    def extract_from_city(self, query: str) -> Optional[str]:
        patterns = [
            re.compile(r'(从|自|由)(.+?)去'),
            re.compile(r'(在)(.+?)，?想'),
            re.compile(r'(从|自|由)(.+?)出发'),
            re.compile(r'(从)(.+?)到')
        ]
        
        for pattern in patterns:
            match = pattern.search(query)
            if match:
                from_city = match.group(2).strip()
                for city in DETAILED_CITY_DATA.keys():
                    if city in from_city:
                        return city
        return None

    def get_budget_level(self, budget: float) -> str:
        for level, range_info in self.budget_levels.items():
            if range_info['min'] <= budget < range_info['max']:
                return level
        return '经济型'

    def recommend_season(self, city: str, budget: float) -> str:
        city_data = DETAILED_CITY_DATA.get(city)
        if not city_data:
            return '秋季'
        
        budget_level = self.get_budget_level(budget)
        
        if city in ['三亚', '海口', '西双版纳']:
            if budget_level == '经济型':
                return '夏季'
            return '冬季'
        
        if city in ['哈尔滨']:
            if budget_level == '经济型':
                return '秋季'
            return '冬季'
        
        if city in ['青岛', '大连']:
            if budget_level == '经济型':
                return '春季'
            return '夏季'
        
        return '秋季'

    def calculate_total_budget(self, city: str, days: int, budget: Optional[float], from_city: Optional[str]) -> Dict:
        city_data = DETAILED_CITY_DATA.get(city, {})
        attractions = city_data.get('景点', [])
        hotels = city_data.get('酒店', [])
        foods = city_data.get('美食', [])

        total = {
            'transport': 0,
            'accommodation': 0,
            'attractions': 0,
            'food': 0,
            'total': 0,
            'user_budget': budget,
            'is_over_budget': False
        }

        if from_city:
            route = self.train_routes.get((from_city, city))
            if route:
                train_price = route['price']
                if budget and train_price * 2 > budget * 0.5:
                    hard_seat_price = int(train_price * 0.5)
                    total['transport'] = hard_seat_price * 2
                    total['transport_note'] = f'已选择硬座（高铁{train_price}元，硬座{hard_seat_price}元）'
                else:
                    total['transport'] = train_price * 2
            else:
                total['transport'] = 500 * 2

        hotel_budget_level = '经济型'
        if hotels and budget:
            transport_cost = total['transport']
            remaining_budget = budget - transport_cost
            
            if remaining_budget > 0:
                per_day_budget = remaining_budget / days
                if per_day_budget >= 500:
                    hotel_budget_level = '舒适型'
                elif per_day_budget >= 1200:
                    hotel_budget_level = '豪华型'
        
        for hotel in hotels:
            if hotel['档次'] == hotel_budget_level:
                price_range = hotel['价格']
                try:
                    min_price = float(price_range.split('-')[0].replace('元/晚', '').replace('元', ''))
                    total['accommodation'] = min_price * (days - 1)
                except:
                    total['accommodation'] = 200 * (days - 1)
                break
        if total['accommodation'] == 0:
            total['accommodation'] = 200 * (days - 1)

        if attractions and budget:
            transport_accommodation = total['transport'] + total['accommodation']
            remaining_for_food_attractions = budget - transport_accommodation
            
            if remaining_for_food_attractions > 0:
                food_budget = remaining_for_food_attractions * 0.6
                attraction_budget = remaining_for_food_attractions * 0.4
                
                avg_food_per_day = food_budget / days
                
                free_attrs = [a for a in attractions if a['票价'] == '免费']
                paid_attrs = [a for a in attractions if a['票价'] != '免费']
                
                sorted_paid_attrs = sorted(paid_attrs, key=lambda x: float(x['票价'].replace('元', '')) if x['票价'] != '免费' else 0)
                
                selected_attrs = free_attrs[:3]
                
                current_attr_cost = 0
                for attr in sorted_paid_attrs:
                    try:
                        price = float(attr['票价'].replace('元', ''))
                        if current_attr_cost + price <= attraction_budget:
                            selected_attrs.append(attr)
                            current_attr_cost += price
                    except:
                        pass
                
                total['attractions'] = current_attr_cost
                
                if foods:
                    for food in foods:
                        try:
                            price_str = food['人均'].replace('元', '').strip()
                            if '-' in price_str:
                                price_str = price_str.split('-')[0]
                            price_str = price_str.split(' ')[0] if ' ' in price_str else price_str
                            price = float(price_str)
                            if price <= avg_food_per_day / 3:
                                total['food'] = price * 3 * days
                                break
                        except:
                            pass
                    if total['food'] == 0:
                        total['food'] = min(avg_food_per_day, 60) * days
            else:
                total['attractions'] = 0
                total['food'] = 60 * 3 * days
        else:
            free_attrs = [a for a in attractions if a['票价'] == '免费']
            for attr in free_attrs[:4]:
                total['attractions'] = 0
            
            if foods:
                avg_per_person = 50
                for food in foods[:4]:
                    try:
                        price_str = food['人均'].replace('元', '').strip()
                        if '-' in price_str:
                            price_str = price_str.split('-')[0]
                        price_str = price_str.split(' ')[0] if ' ' in price_str else price_str
                        price = float(price_str)
                        avg_per_person = price
                        break
                    except:
                        pass
                total['food'] = avg_per_person * 3 * days

        total['total'] = total['transport'] + total['accommodation'] + total['attractions'] + total['food']
        
        if budget and total['total'] > budget:
            total['is_over_budget'] = True

        return total

    def generate_travel_plan(self, query: str) -> Dict:
        city = self.extract_city(query)
        season = self.extract_season(query)
        days = self.extract_days(query)
        budget = self.extract_budget(query)
        from_city = self.extract_from_city(query)
        
        if not city and not season:
            return {'success': False, 'error': '无法识别城市或季节，请提供更具体的信息'}
        
        if not city:
            return self._generate_season_plan(season, days, budget)
        
        if not season and budget:
            season = self.recommend_season(city, budget)
        
        if not days and budget:
            budget_level = self.get_budget_level(budget)
            days = self.budget_levels[budget_level]['days']
        
        return self._generate_city_plan(city, season, days, budget, from_city)

    def _generate_city_plan(self, city: str, season: Optional[str], days: Optional[int], budget: Optional[float], from_city: Optional[str]) -> Dict:
        city_data = DETAILED_CITY_DATA.get(city)
        if not city_data:
            return {'success': False, 'error': f'暂未收录{city}的详细信息'}
        
        if days is None:
            days = 3
        
        if budget and from_city:
            route = self.train_routes.get((from_city, city))
            if route:
                transport_cost = route['price'] * 2
                if transport_cost > budget * 0.6:
                    days = max(2, days - 1)
                if transport_cost > budget * 0.8:
                    days = 2
        
        plan_key = str(days) + '天' if str(days) + '天' in city_data['路线'] else '3天'
        route = city_data['路线'].get(plan_key, city_data['路线']['3天'])
        
        budget_level = self.get_budget_level(budget) if budget else '舒适型'
        season = season or self.recommend_season(city, budget) if budget else '秋季'
        
        budget_details = self.calculate_total_budget(city, days, budget, from_city)
        
        plan = {
            'success': True,
            'city': city,
            'season': season,
            'days': days,
            'budget': budget,
            'budget_level': budget_level,
            'from_city': from_city,
            'title': f'{city}{days}日游详细行程',
            'description': f'{self._generate_description(city, season, days, budget, from_city)}',
            'daily_plan': [],
            'hotels': [],
            'foods': [],
            'tips': [],
            'transport': [],
            'budget_details': budget_details,
            'attractions': []
        }
        
        for day in route:
            day_plan = {
                'day': day['天数'],
                'morning': day['上午'],
                'afternoon': day['下午'],
                'evening': day['晚上'],
                'attractions': [],
                'meals': [],
                'estimated_cost': 0
            }
            
            morning_parts = [p.strip() for p in day['上午'].replace('→', ',').replace('，', ',').split(',') if p.strip()]
            afternoon_parts = [p.strip() for p in day['下午'].replace('→', ',').replace('，', ',').split(',') if p.strip()]
            
            day_cost = 0
            for part in morning_parts + afternoon_parts:
                for attraction in city_data['景点']:
                    if attraction['名称'] in part:
                        day_plan['attractions'].append(attraction)
                        plan['attractions'].append(attraction)
                        try:
                            price = float(attraction['票价'].replace('元', ''))
                            day_cost += price
                        except:
                            pass
                        break
            
            day_plan['estimated_cost'] = day_cost
            plan['daily_plan'].append(day_plan)
        
        plan['hotels'] = self._filter_hotels_by_budget(city_data['酒店'], budget)
        plan['foods'] = city_data['美食'][:4]
        
        if from_city:
            plan['transport'].append(self._generate_transport_info(from_city, city))
        
        self._generate_tips(plan, city_data)
        
        return plan

    def _generate_description(self, city: str, season: str, days: int, budget: Optional[float], from_city: Optional[str]) -> str:
        desc = f'{city}是一座充满魅力的城市，{season}是去{city}旅游的好时节'
        if budget:
            desc += f'，您的预算{budget}元属于{self.get_budget_level(budget)}'
        if from_city:
            desc += f'，从{from_city}出发'
        
        if budget and from_city:
            route = self.train_routes.get((from_city, city))
            if route and route['price'] * 2 > budget * 0.6:
                desc += f'，由于预算限制，已为您调整为{days}天行程'
            else:
                desc += f'，建议游玩{days}天'
        else:
            desc += f'，建议游玩{days}天'
            
        return desc

    def _filter_hotels_by_budget(self, hotels: List[Dict], budget: Optional[float]) -> List[Dict]:
        if not budget:
            return hotels[:3]
        
        budget_per_day = budget / 3
        
        suitable_hotels = []
        for hotel in hotels:
            try:
                price_range = hotel['价格']
                min_price = float(price_range.split('-')[0].replace('元/晚', '').replace('元', ''))
                if min_price <= budget_per_day * 1.5:
                    suitable_hotels.append(hotel)
            except:
                suitable_hotels.append(hotel)
        
        return suitable_hotels[:3]

    def _generate_transport_info(self, from_city: str, to_city: str) -> Dict:
        transport_options = []
        
        route = self.train_routes.get((from_city, to_city))
        if route:
            transport_options.append({
                'type': '高铁',
                'train': route['train'],
                'duration': route['duration'],
                'price': f'{route["price"]}元',
                'frequency': '每天1-2班'
            })
        
        base_price = route['price'] if route else 500
        transport_options.append({
            'type': '飞机',
            'duration': self._estimate_flight_duration(from_city, to_city),
            'price': f'{int(base_price * 1.5)}元起',
            'frequency': '每天多班次'
        })
        
        transport_options.append({
            'type': '自驾',
            'duration': self._estimate_drive_duration(from_city, to_city),
            'price': f'{int(base_price * 0.8)}元(油费+过路费)',
            'frequency': '随时出发'
        })
        
        return {
            'from': from_city,
            'to': to_city,
            'options': transport_options
        }

    def _estimate_flight_duration(self, from_city: str, to_city: str) -> str:
        distances = {
            ("北京", "三亚"): "3.5小时",
            ("北京", "上海"): "2小时",
            ("北京", "杭州"): "2.5小时",
            ("北京", "成都"): "3小时",
            ("北京", "西安"): "2小时",
            ("上海", "杭州"): "1小时",
            ("上海", "广州"): "2.5小时",
            ("成都", "西安"): "1.5小时",
            ("广州", "三亚"): "1.5小时",
            ("广州", "桂林"): "1小时"
        }
        return distances.get((from_city, to_city), "2-3小时")

    def _estimate_drive_duration(self, from_city: str, to_city: str) -> str:
        distances = {
            ("北京", "上海"): "12小时",
            ("北京", "杭州"): "14小时",
            ("北京", "西安"): "11小时",
            ("上海", "杭州"): "2小时",
            ("成都", "西安"): "8小时",
            ("广州", "桂林"): "6小时"
        }
        return distances.get((from_city, to_city), "6-12小时")

    def _generate_tips(self, plan: Dict, city_data: Dict):
        city = plan['city']
        season = plan['season']
        budget = plan['budget']
        budget_details = plan.get('budget_details', {})
        from_city = plan.get('from_city')
        
        if season:
            warm_cities = ['三亚', '海口', '西双版纳', '昆明']
            cold_cities = ['哈尔滨', '北京', '西安', '南京']
            
            if season == '冬季':
                if city in warm_cities:
                    plan['tips'].append(f'{season}去{city}，气候温暖舒适，是避寒好去处')
                else:
                    plan['tips'].append(f'{season}去{city}，注意保暖，建议携带羽绒服')
            elif season == '夏季':
                if city in ['青岛', '大连', '威海']:
                    plan['tips'].append(f'{season}去{city}，海风凉爽，适合避暑')
                else:
                    plan['tips'].append(f'{season}去{city}，注意防晒防暑，携带雨具')
            elif season == '春季':
                plan['tips'].append(f'{season}去{city}，天气多变，建议携带外套')
            else:
                plan['tips'].append(f'{season}去{city}，气候宜人，是旅游好时节')
        
        if budget and budget_details.get('is_over_budget'):
            plan['tips'].append(f'⚠️ 当前方案总费用{budget_details["total"]:.0f}元，超出您的预算{budget}元')
            
            transport_cost = budget_details.get('transport', 0)
            if transport_cost > budget:
                plan['tips'].append(f'🚄 仅交通费{transport_cost}元已超出预算，建议考虑：')
                
                if from_city:
                    cheaper_options = []
                    for dest_city in DETAILED_CITY_DATA.keys():
                        if dest_city == city:
                            continue
                        route = self.train_routes.get((from_city, dest_city))
                        if route and route['price'] * 2 <= budget * 0.5:
                            cheaper_options.append(f'{dest_city}（高铁{route["price"]}元）')
                    
                    if cheaper_options:
                        plan['tips'].append(f'   推荐更近的目的地：{", ".join(cheaper_options[:3])}')
            
            plan['tips'].append('💡 建议缩短游玩天数或选择免费景点以控制预算')
        
        elif budget:
            remaining = budget - budget_details.get('total', 0)
            if remaining > 0:
                plan['tips'].append(f'✅ 当前方案总费用{budget_details["total"]:.0f}元，预算内剩余{remaining:.0f}元')
        
        if budget:
            budget_level = plan['budget_level']
            if budget_level == '经济型':
                plan['tips'].append('💰 预算较为紧张，已为您优先选择免费景点和经济型酒店')
            elif budget_level == '舒适型':
                plan['tips'].append('💰 预算适中，可以兼顾品质与性价比')
            else:
                plan['tips'].append('💰 预算充足，可以选择高品质住宿和体验')
        
        plan['tips'].append(f'{city}热门景点建议提前预约，避免排队')
        plan['tips'].append('出行前关注天气预报，合理安排行程')

    def _generate_season_plan(self, season: str, days: Optional[int], budget: Optional[float]) -> Dict:
        cities = self.season_cities.get(season, [])
        
        if days is None:
            days = 3
        
        plan = {
            'success': True,
            'season': season,
            'days': days,
            'budget': budget,
            'title': f'{season}{days}日游推荐行程',
            'description': f'{season}是出游的好时节，以下是为您推荐的{days}日游方案',
            'recommendations': []
        }
        
        budget_level = self.get_budget_level(budget) if budget else '舒适型'
        
        for city in cities[:3]:
            city_data = DETAILED_CITY_DATA.get(city)
            if city_data:
                rec = {
                    'city': city,
                    'description': city_data['景点'][0]['名称'],
                    'rating': city_data['景点'][0]['评分'],
                    'price_range': city_data['酒店'][-1]['价格'].split('-')[0] + '-' + city_data['酒店'][0]['价格'].split('-')[1],
                    'best_attractions': [a['名称'] for a in city_data['景点'][:3]],
                    'special_food': [f['名称'] for f in city_data['美食'][:3]],
                    'budget_friendly': budget_level == '经济型' and any('经济' in h['档次'] for h in city_data['酒店'])
                }
                plan['recommendations'].append(rec)
        
        return plan


travel_planner = TravelPlanner()