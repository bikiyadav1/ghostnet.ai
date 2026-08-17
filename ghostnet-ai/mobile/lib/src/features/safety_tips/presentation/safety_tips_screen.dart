import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

class SafetyTipsScreen extends StatefulWidget {
  const SafetyTipsScreen({Key? key}) : super(key: key);

  @override
  State<SafetyTipsScreen> createState() => _SafetyTipsScreenState();
}

class _SafetyTipsScreenState extends State<SafetyTipsScreen> {
  String _selectedLang = 'en'; // 'en' or 'hi'
  List<dynamic> _protocols = [];
  bool _isLoading = true;

  @override
  void initState() {
    super.initState();
    _loadBundledTips();
  }

  Future<void> _loadBundledTips() async {
    try {
      final jsonStr = await rootBundle.loadString('assets/data/safety_tips.json');
      final Map<String, dynamic> data = jsonDecode(jsonStr);
      if (mounted) {
        setState(() {
          _protocols = data['safety_protocols'] ?? [];
          _isLoading = false;
        });
      }
    } catch (e) {
      // Fallback hardcoded in case bundle loader during test
      if (mounted) {
        setState(() {
          _protocols = [
            {
              "id": "flood",
              "category": "Flood & Inundation",
              "category_hi": "बाढ़ और जलभराव",
              "steps_en": [
                "Move immediately to higher ground or designated relief shelter.",
                "Turn off main electricity switch and gas valves before leaving.",
                "Do not walk or drive through moving flood waters."
              ],
              "steps_hi": [
                "तुरंत ऊंचे स्थान या निर्दिष्ट राहत शिविर की ओर जाएं।",
                "घर छोड़ने से पहले मुख्य बिजली का स्विच और गैस वाल्व बंद कर दें।",
                "बहते बाढ़ के पानी में पैदल या वाहन से न जाएं।"
              ]
            }
          ];
          _isLoading = false;
        });
      }
    }
  }

  IconData _getIconForProtocol(String id) {
    switch (id) {
      case 'flood':
        return Icons.water_damage_rounded;
      case 'earthquake':
        return Icons.vibration_rounded;
      case 'cyclone':
        return Icons.air_rounded;
      default:
        return Icons.health_and_safety_rounded;
    }
  }

  @override
  Widget build(BuildContext context) {
    final isHindi = _selectedLang == 'hi';

    return Scaffold(
      backgroundColor: const Color(0xFF0B0F19),
      appBar: AppBar(
        backgroundColor: const Color(0xFF111827),
        elevation: 0,
        title: Text(
          isHindi ? 'ऑफ़लाइन सुरक्षा सुझाव' : 'Offline Safety Protocols',
          style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16, color: Colors.white),
        ),
        actions: [
          // Language Switcher Toggle
          Container(
            margin: const EdgeInsets.symmetric(vertical: 10, horizontal: 12),
            decoration: BoxDecoration(
              color: const Color(0xFF1F2937),
              borderRadius: BorderRadius.circular(10),
              border: Border.all(color: Colors.white12),
            ),
            child: Row(
              children: [
                GestureDetector(
                  onTap: () => setState(() => _selectedLang = 'en'),
                  child: Container(
                    padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                    decoration: BoxDecoration(
                      color: !isHindi ? const Color(0xFF00F0FF) : Colors.transparent,
                      borderRadius: BorderRadius.circular(8),
                    ),
                    child: Text(
                      'EN',
                      style: TextStyle(
                        fontSize: 11,
                        fontWeight: FontWeight.bold,
                        color: !isHindi ? Colors.black : Colors.white60,
                      ),
                    ),
                  ),
                ),
                GestureDetector(
                  onTap: () => setState(() => _selectedLang = 'hi'),
                  child: Container(
                    padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                    decoration: BoxDecoration(
                      color: isHindi ? const Color(0xFF00F0FF) : Colors.transparent,
                      borderRadius: BorderRadius.circular(8),
                    ),
                    child: Text(
                      'हिन्दी',
                      style: TextStyle(
                        fontSize: 11,
                        fontWeight: FontWeight.bold,
                        color: isHindi ? Colors.black : Colors.white60,
                      ),
                    ),
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator(color: Color(0xFF00F0FF)))
          : ListView.builder(
              padding: const EdgeInsets.all(16.0),
              itemCount: _protocols.length,
              itemBuilder: (context, index) {
                final proto = _protocols[index];
                final title = isHindi ? (proto['category_hi'] ?? proto['category']) : proto['category'];
                final steps = isHindi ? (proto['steps_hi'] ?? proto['steps_en']) : proto['steps_en'];

                return Card(
                  color: const Color(0xFF111827),
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(16),
                    side: const BorderSide(color: Colors.white10),
                  ),
                  margin: const EdgeInsets.only(bottom: 16),
                  child: Padding(
                    padding: const EdgeInsets.all(16.0),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          children: [
                            Container(
                              padding: const EdgeInsets.all(10),
                              decoration: BoxDecoration(
                                color: const Color(0xFF00F0FF).withOpacity(0.15),
                                borderRadius: BorderRadius.circular(12),
                              ),
                              child: Icon(
                                _getIconForProtocol(proto['id'] ?? ''),
                                color: const Color(0xFF00F0FF),
                                size: 22,
                              ),
                            ),
                            const SizedBox(width: 12),
                            Expanded(
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text(
                                    title,
                                    style: const TextStyle(
                                      color: Colors.white,
                                      fontSize: 15,
                                      fontWeight: FontWeight.bold,
                                    ),
                                  ),
                                  Text(
                                    isHindi ? '100% ऑफ़लाइन उपलब्ध' : 'Zero Network Required',
                                    style: const TextStyle(color: Color(0xFF10B981), fontSize: 10),
                                  ),
                                ],
                              ),
                            ),
                          ],
                        ),
                        const SizedBox(height: 14),
                        const Divider(color: Colors.white10, height: 1),
                        const SizedBox(height: 12),
                        ...(steps as List<dynamic>).map((step) {
                          return Padding(
                            padding: const EdgeInsets.symmetric(vertical: 4.0),
                            child: Row(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                const Text(
                                  "• ",
                                  style: TextStyle(color: Color(0xFF00F0FF), fontWeight: FontWeight.bold, fontSize: 14),
                                ),
                                Expanded(
                                  child: Text(
                                    step.toString(),
                                    style: const TextStyle(color: Colors.white70, fontSize: 12, height: 1.35),
                                  ),
                                ),
                              ],
                            ),
                          );
                        }).toList(),
                      ],
                    ),
                  ),
                );
              },
            ),
    );
  }
}
