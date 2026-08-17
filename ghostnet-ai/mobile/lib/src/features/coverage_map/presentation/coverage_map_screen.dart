import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:latlong2/latlong.dart';
import '../../../core/database/app_database.dart';
import '../../../core/network/api_client.dart';
import '../../../core/services/location_sampler.dart';
import '../../../core/services/sync_manager.dart';
import 'widgets/help_points_sheet.dart';

class CoverageMapScreen extends StatefulWidget {
  final AppDatabase database;
  final ApiClient apiClient;

  const CoverageMapScreen({
    Key? key,
    required this.database,
    required this.apiClient,
  }) : super(key: key);

  @override
  State<CoverageMapScreen> createState() => _CoverageMapScreenState();
}

class _CoverageMapScreenState extends State<CoverageMapScreen> {
  late LocationSignalSampler _sampler;
  late SyncManager _syncManager;

  LatLng _currentLocation = const LatLng(23.1950, 86.0468); // In/Near Ajodhya Hills ridge
  int _currentDbm = -118;
  String _networkType = '2G';
  bool _isSampling = false;
  bool _isInDeadZone = true; // Proactive ML geofence check
  List<Map<String, dynamic>> _helpPoints = [];
  List<Map<String, dynamic>> _heatmapCells = [];

  @override
  void initState() {
    super.initState();
    _sampler = LocationSignalSampler(database: widget.database);
    _syncManager = SyncManager(database: widget.database, apiClient: widget.apiClient);
    _loadInitialData();
  }

  Future<void> _loadInitialData() async {
    final hp = await widget.apiClient.fetchHelpPoints(
      lat: _currentLocation.latitude,
      lon: _currentLocation.longitude,
      radiusKm: 40,
    );
    final heat = await widget.apiClient.fetchCoverageHeatmap();
    if (mounted) {
      setState(() {
        _helpPoints = hp;
        _heatmapCells = heat;
      });
    }
  }

  Future<void> _triggerSampleAndSync() async {
    setState(() => _isSampling = true);
    await _sampler.sampleAndStore();
    final syncResults = await _syncManager.syncAllPending();
    final syncedReadings = syncResults['readings'] ?? 0;

    if (mounted) {
      setState(() {
        _isSampling = false;
      });

      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            syncedReadings > 0
                ? 'Synced $syncedReadings telemetry readings to dashboard!'
                : 'Offline: Telemetry queued locally in SQLite database.',
          ),
          backgroundColor: const Color(0xFF10B981),
          duration: const Duration(seconds: 2),
        ),
      );
    }
  }

  Color _getSignalColor(int dbm) {
    if (dbm >= -80) return const Color(0xFF10B981);
    if (dbm >= -100) return const Color(0xFFF59E0B);
    return const Color(0xFFF43F5E);
  }

  @override
  Widget build(BuildContext context) {
    final signalColor = _getSignalColor(_currentDbm);

    return Scaffold(
      backgroundColor: const Color(0xFF0B0F19),
      body: Stack(
        children: [
          // Flutter Map Layer
          FlutterMap(
            options: MapOptions(
              initialCenter: _currentLocation,
              initialZoom: 11.5,
            ),
            children: [
              TileLayer(
                urlTemplate: 'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png',
                subdomains: const ['a', 'b', 'c', 'd'],
              ),
              // Heatmap grid circles
              CircleLayer(
                circles: _heatmapCells.map((c) {
                  final dbm = (c['avg_signal_dbm'] as num?)?.toInt() ?? -90;
                  final color = _getSignalColor(dbm);
                  return CircleMarker(
                    point: LatLng(
                      (c['lat'] as num).toDouble(),
                      (c['lon'] as num).toDouble(),
                    ),
                    radius: 18,
                    useRadiusInMeter: false,
                    color: color.withOpacity(0.35),
                    borderColor: color.withOpacity(0.6),
                    borderStrokeWidth: 1,
                  );
                }).toList(),
              ),
              // Current Device Location Marker
              MarkerLayer(
                markers: [
                  Marker(
                    point: _currentLocation,
                    width: 44,
                    height: 44,
                    child: Container(
                      decoration: BoxDecoration(
                        color: const Color(0xFF00F0FF).withOpacity(0.25),
                        shape: BoxShape.circle,
                      ),
                      child: Center(
                        child: Container(
                          width: 18,
                          height: 18,
                          decoration: const BoxDecoration(
                            color: Color(0xFF00F0FF),
                            shape: BoxShape.circle,
                            boxShadow: [
                              BoxShadow(color: Color(0xFF00F0FF), blurRadius: 10),
                            ],
                          ),
                        ),
                      ),
                    ),
                  ),
                ],
              ),
            ],
          ),

          // Header Status Bar & Proactive Geofence Warning
          SafeArea(
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
              child: Column(
                children: [
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      // Brand Pill
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
                        decoration: BoxDecoration(
                          color: const Color(0xFF111827).withOpacity(0.9),
                          borderRadius: BorderRadius.circular(16),
                          border: Border.all(color: Colors.white12),
                          boxShadow: const [BoxShadow(color: Colors.black45, blurRadius: 8)],
                        ),
                        child: const Row(
                          children: [
                            Icon(Icons.radio_rounded, color: Color(0xFF00F0FF), size: 18),
                            SizedBox(width: 8),
                            Text(
                              'GhostNet Mobile',
                              style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 13),
                            ),
                          ],
                        ),
                      ),

                      // Telemetry Signal Pill
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                        decoration: BoxDecoration(
                          color: const Color(0xFF111827).withOpacity(0.9),
                          borderRadius: BorderRadius.circular(16),
                          border: Border.all(color: signalColor.withOpacity(0.4)),
                        ),
                        child: Row(
                          children: [
                            Container(
                              width: 8,
                              height: 8,
                              decoration: BoxDecoration(
                                color: signalColor,
                                shape: BoxShape.circle,
                                boxShadow: [BoxShadow(color: signalColor, blurRadius: 6)],
                              ),
                            ),
                            const SizedBox(width: 8),
                            Text(
                              '$_currentDbm dBm ($_networkType)',
                              style: TextStyle(color: signalColor, fontWeight: FontWeight.bold, fontSize: 12),
                            ),
                          ],
                        ),
                      ),
                    ],
                  ),

                  // Proactive ML Dead-Zone Geofence Alert Banner
                  if (_isInDeadZone) ...[
                    const SizedBox(height: 10),
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
                      decoration: BoxDecoration(
                        color: const Color(0xFF881337).withOpacity(0.9),
                        borderRadius: BorderRadius.circular(14),
                        border: Border.all(color: const Color(0xFFF43F5E)),
                        boxShadow: [
                          BoxShadow(color: const Color(0xFFF43F5E).withOpacity(0.3), blurRadius: 10)
                        ],
                      ),
                      child: const Row(
                        children: [
                          Icon(Icons.warning_amber_rounded, color: Colors.white, size: 18),
                          SizedBox(width: 8),
                          Expanded(
                            child: Text(
                              'AI Alert: Entering a weak-signal dead zone (Ajodhya Hills). Offline SOS is primed & ready.',
                              style: TextStyle(color: Colors.white, fontSize: 11, fontWeight: FontWeight.w600),
                            ),
                          ),
                        ],
                      ),
                    ),
                  ],
                ],
              ),
            ),
          ),

          // Bottom Action Floater
          Positioned(
            bottom: 24,
            left: 16,
            right: 16,
            child: Row(
              children: [
                Expanded(
                  flex: 2,
                  child: ElevatedButton.icon(
                    onPressed: _isSampling ? null : _triggerSampleAndSync,
                    icon: _isSampling
                        ? const SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.black))
                        : const Icon(Icons.send_rounded, size: 18, color: Colors.black),
                    label: Text(
                      _isSampling ? 'Sampling...' : 'Sample & Sync Telemetry',
                      style: const TextStyle(color: Colors.black, fontWeight: FontWeight.bold, fontSize: 13),
                    ),
                    style: ElevatedButton.styleFrom(
                      backgroundColor: const Color(0xFF00F0FF),
                      padding: const EdgeInsets.symmetric(vertical: 14),
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
                      elevation: 6,
                    ),
                  ),
                ),
                const SizedBox(width: 12),
                ElevatedButton(
                  onPressed: () {
                    showModalBottomSheet(
                      context: context,
                      backgroundColor: Colors.transparent,
                      isScrollControlled: true,
                      builder: (_) => HelpPointsSheet(helpPoints: _helpPoints),
                    );
                  },
                  style: ElevatedButton.styleFrom(
                    backgroundColor: const Color(0xFF1F2937),
                    padding: const EdgeInsets.all(14),
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
                    side: const BorderSide(color: Colors.white12),
                  ),
                  child: const Icon(Icons.emergency_rounded, color: Color(0xFFF43F5E), size: 22),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
