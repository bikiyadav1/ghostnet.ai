import 'dart:convert';
import 'dart:io';
import 'package:http/http.dart' as http;

class ApiClient {
  static String get baseUrl {
    if (Platform.isAndroid) {
      return 'http://10.0.2.2:8000/api/v1';
    }
    return 'http://localhost:8000/api/v1';
  }

  final http.Client _client;

  ApiClient({http.Client? client}) : _client = client ?? http.Client();

  // POST /readings
  Future<bool> submitReadingsBatch(List<Map<String, dynamic>> readings) async {
    if (readings.isEmpty) return true;
    try {
      final response = await _client.post(
        Uri.parse('$baseUrl/readings'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({'readings': readings}),
      );
      return response.statusCode == 201;
    } catch (e) {
      print('[ApiClient] Error uploading readings: $e');
      return false;
    }
  }

  // POST /sos/batch (Sync on reconnect)
  Future<bool> submitSosBatch(List<Map<String, dynamic>> alerts) async {
    if (alerts.isEmpty) return true;
    try {
      final response = await _client.post(
        Uri.parse('$baseUrl/sos/batch'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({'alerts': alerts}),
      );
      return response.statusCode == 201;
    } catch (e) {
      print('[ApiClient] Error uploading SOS alerts batch: $e');
      return false;
    }
  }

  // POST /check-in
  Future<bool> submitCheckIn({
    required String deviceId,
    required double lat,
    required double lon,
    String status = 'safe',
  }) async {
    try {
      final response = await _client.post(
        Uri.parse('$baseUrl/check-in'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({
          'device_id': deviceId,
          'lat': lat,
          'lon': lon,
          'status': status,
        }),
      );
      return response.statusCode == 201;
    } catch (e) {
      print('[ApiClient] Error submitting check-in: $e');
      return false;
    }
  }

  // GET /coverage/heatmap
  Future<List<Map<String, dynamic>>> fetchCoverageHeatmap({String? bbox}) async {
    try {
      final uri = bbox != null
          ? Uri.parse('$baseUrl/coverage/heatmap?bbox=$bbox')
          : Uri.parse('$baseUrl/coverage/heatmap');
      final response = await _client.get(uri);
      if (response.statusCode == 200) {
        final List<dynamic> data = jsonDecode(response.body);
        return data.cast<Map<String, dynamic>>();
      }
    } catch (e) {
      print('[ApiClient] Error fetching heatmap: $e');
    }
    return [];
  }

  // GET /help-points
  Future<List<Map<String, dynamic>>> fetchHelpPoints({
    required double lat,
    required double lon,
    double radiusKm = 25.0,
  }) async {
    try {
      final uri = Uri.parse('$baseUrl/help-points?lat=$lat&lon=$lon&radius_km=$radiusKm');
      final response = await _client.get(uri);
      if (response.statusCode == 200) {
        final List<dynamic> data = jsonDecode(response.body);
        return data.cast<Map<String, dynamic>>();
      }
    } catch (e) {
      print('[ApiClient] Error fetching help points: $e');
    }
    return [];
  }
}
