import 'package:connectivity_plus/connectivity_plus.dart';
import '../database/app_database.dart';
import '../network/api_client.dart';

class SyncManager {
  final AppDatabase database;
  final ApiClient apiClient;

  SyncManager({required this.database, required this.apiClient});

  // Comprehensive sync for telemetry, SOS emergency alerts, and check-ins
  Future<Map<String, int>> syncAllPending() async {
    final stats = {'readings': 0, 'sos': 0, 'checkins': 0};
    try {
      final connectivityResult = await Connectivity().checkConnectivity();
      if (connectivityResult.contains(ConnectivityResult.none)) {
        print('[SyncManager] Device offline. Preserving local SQLite queues.');
        return stats;
      }

      // 1. Sync Priority SOS Alerts first (Critical)
      final unsyncedSos = await database.getUnsyncedSosAlerts(limit: 20);
      if (unsyncedSos.isNotEmpty) {
        final sosPayload = unsyncedSos.map((s) => {
          'device_id': s.deviceId,
          'lat': s.lat,
          'lon': s.lon,
          'category': s.category,
          'message': s.message,
          'offline_created_at': s.offlineCreatedAt.toIso8601String(),
          'is_relayed': s.isRelayed,
        }).toList();

        final sosSuccess = await apiClient.submitSosBatch(sosPayload);
        if (sosSuccess) {
          final ids = unsyncedSos.map((s) => s.id).toList();
          await database.markSosAlertsSynced(ids);
          stats['sos'] = ids.length;
          print('[SyncManager] Synced ${ids.length} offline SOS alerts to dashboard!');
        }
      }

      // 2. Sync Check-Ins
      final unsyncedCheckins = await database.getUnsyncedCheckIns(limit: 20);
      for (final ci in unsyncedCheckins) {
        final ciSuccess = await apiClient.submitCheckIn(
          deviceId: ci.deviceId,
          lat: ci.lat,
          lon: ci.lon,
          status: ci.status,
        );
        if (ciSuccess) {
          await database.markCheckInsSynced([ci.id]);
          stats['checkins'] = (stats['checkins'] ?? 0) + 1;
        }
      }

      // 3. Sync Background Signal Telemetry
      final unsyncedReadings = await database.getUnsyncedReadings(limit: 100);
      if (unsyncedReadings.isNotEmpty) {
        final readingsPayload = unsyncedReadings.map((r) => {
          'device_id': r.deviceId,
          'lat': r.lat,
          'lon': r.lon,
          'network_type': r.networkType,
          'signal_dbm': r.signalDbm,
          'download_mbps': r.downloadMbps,
          'upload_mbps': r.uploadMbps,
          'latency_ms': r.latencyMs,
          'recorded_at': r.recordedAt.toIso8601String(),
        }).toList();

        final readSuccess = await apiClient.submitReadingsBatch(readingsPayload);
        if (readSuccess) {
          final ids = unsyncedReadings.map((r) => r.id).toList();
          await database.markReadingsSynced(ids);
          stats['readings'] = ids.length;
        }
      }
    } catch (e) {
      print('[SyncManager] Error during sync: $e');
    }
    return stats;
  }
}
