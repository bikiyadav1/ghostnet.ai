import 'package:flutter/material.dart';

class HelpPointsSheet extends StatelessWidget {
  final List<Map<String, dynamic>> helpPoints;

  const HelpPointsSheet({Key? key, required this.helpPoints}) : super(key: key);

  IconData _getIconForType(String type) {
    switch (type) {
      case 'hospital':
        return Icons.local_hospital_rounded;
      case 'police':
        return Icons.local_police_rounded;
      case 'shelter':
        return Icons.holiday_village_rounded;
      case 'safe_zone':
      default:
        return Icons.flag_rounded;
    }
  }

  Color _getColorForType(String type) {
    switch (type) {
      case 'hospital':
        return const Color(0xFFF43F5E);
      case 'police':
        return const Color(0xFF3B82F6);
      case 'shelter':
        return const Color(0xFFF59E0B);
      case 'safe_zone':
      default:
        return const Color(0xFF10B981);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: const BoxDecoration(
        color: Color(0xFF111827),
        borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
      ),
      padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 16),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Center(
            child: Container(
              width: 40,
              height: 4,
              decoration: BoxDecoration(
                color: Colors.white24,
                borderRadius: BorderRadius.circular(2),
              ),
            ),
          ),
          const SizedBox(height: 16),
          Row(
            mainAxisAlignment: MainAxisAlignment.between,
            children: [
              const Text(
                'Nearby Emergency Help Points',
                style: TextStyle(
                  color: Colors.white,
                  fontSize: 16,
                  fontWeight: FontWeight.bold,
                ),
              ),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                decoration: BoxDecoration(
                  color: const Color(0xFF1F2937),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Text(
                  '${helpPoints.length} Found',
                  style: const TextStyle(color: Color(0xFF00F0FF), fontSize: 12),
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          ConstrainedBox(
            constraints: const BoxConstraints(maxHeight: 340),
            child: helpPoints.isEmpty
                ? const Center(
                    child: Padding(
                      padding: EdgeInsets.all(24.0),
                      child: Text(
                        'No help points nearby or loading...',
                        style: TextStyle(color: Colors.white54, fontSize: 13),
                      ),
                    ),
                  )
                : ListView.separated(
                    shrinkWrap: true,
                    itemCount: helpPoints.length,
                    separatorBuilder: (_, __) => const Divider(color: Colors.white10),
                    itemBuilder: (context, index) {
                      final hp = helpPoints[index];
                      final type = hp['type'] ?? 'safe_zone';
                      final color = _getColorForType(type);

                      return ListTile(
                        contentPadding: EdgeInsets.zero,
                        leading: Container(
                          padding: const EdgeInsets.all(10),
                          decoration: BoxDecoration(
                            color: color.withOpacity(0.15),
                            borderRadius: BorderRadius.circular(12),
                          ),
                          child: Icon(_getIconForType(type), color: color, size: 20),
                        ),
                        title: Text(
                          hp['name'] ?? 'Help Point',
                          style: const TextStyle(
                            color: Colors.white,
                            fontSize: 14,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                        subtitle: Text(
                          '${type.toString().toUpperCase().replaceAll('_', ' ')} · ${hp['distance_km'] ?? '?'} km away',
                          style: TextStyle(color: color.withOpacity(0.8), fontSize: 11),
                        ),
                        trailing: const Icon(Icons.chevron_right_rounded, color: Colors.white38),
                      );
                    },
                  ),
          ),
        ],
      ),
    );
  }
}
