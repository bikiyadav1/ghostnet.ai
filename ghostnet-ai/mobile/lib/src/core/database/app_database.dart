import 'dart:io';
import 'package:drift/drift.dart';
import 'package:drift/native.dart';
import 'package:path_provider/path_provider.dart';
import 'package:path/path.dart' as p;
import 'package:uuid/uuid.dart';

part 'app_database.g.dart';

class LocalSignalReadings extends Table {
  IntColumn get id => integer().autoIncrement()();
  TextColumn get deviceId => text()();
  RealColumn get lat => real()();
  RealColumn get lon => real()();
  TextColumn get networkType => text()();
  IntColumn get signalDbm => integer()();
  RealColumn get downloadMbps => real().withDefault(const Constant(0.0))();
  RealColumn get uploadMbps => real().withDefault(const Constant(0.0))();
  IntColumn get latencyMs => integer().withDefault(const Constant(0))();
  DateTimeColumn get recordedAt => dateTime()();
  BoolColumn get isSynced => boolean().withDefault(const Constant(false))();
}

class LocalSosAlerts extends Table {
  IntColumn get id => integer().autoIncrement()();
  TextColumn get alertId => text()();
  TextColumn get deviceId => text()();
  RealColumn get lat => real()();
  RealColumn get lon => real()();
  TextColumn get category => text()();
  TextColumn get message => text().nullable()();
  TextColumn get status => text().withDefault(const Constant('queued'))();
  DateTimeColumn get offlineCreatedAt => dateTime()();
  BoolColumn get isSynced => boolean().withDefault(const Constant(false))();
  BoolColumn get isRelayed => boolean().withDefault(const Constant(false))();
}

class LocalCheckIns extends Table {
  IntColumn get id => integer().autoIncrement()();
  TextColumn get deviceId => text()();
  RealColumn get lat => real()();
  RealColumn get lon => real()();
  TextColumn get status => text().withDefault(const Constant('safe'))();
  DateTimeColumn get createdAt => dateTime()();
  BoolColumn get isSynced => boolean().withDefault(const Constant(false))();
}

class LocalDeviceConfig extends Table {
  TextColumn get deviceId => text()();
  DateTimeColumn get createdAt => dateTime()();
  TextColumn get appVersion => text().withDefault(const Constant("2.0.0"))();

  @override
  Set<Column> get primaryKey => {deviceId};
}

@DriftDatabase(tables: [
  LocalSignalReadings,
  LocalSosAlerts,
  LocalCheckIns,
  LocalDeviceConfig,
])
class AppDatabase extends _$AppDatabase {
  AppDatabase() : super(_openConnection());

  @override
  int get schemaVersion => 2;

  // Retrieve or initialize anonymous local device UUID
  Future<String> getOrCreateDeviceId() async {
    final existing = await select(localDeviceConfig).getSingleOrNull();
    if (existing != null) {
      return existing.deviceId;
    }

    final newId = const Uuid().v4();
    await into(localDeviceConfig).insert(
      LocalDeviceConfigCompanion(
        deviceId: Value(newId),
        createdAt: Value(DateTime.now().toUtc()),
        appVersion: const Value("2.0.0"),
      ),
    );
    return newId;
  }

  // Insert a newly recorded signal telemetry reading
  Future<int> insertReading({
    required String deviceId,
    required double lat,
    required double lon,
    required String networkType,
    required int signalDbm,
    double downloadMbps = 0.0,
    double uploadMbps = 0.0,
    int latencyMs = 0,
    required DateTime recordedAt,
  }) {
    return into(localSignalReadings).insert(
      LocalSignalReadingsCompanion(
        deviceId: Value(deviceId),
        lat: Value(lat),
        lon: Value(lon),
        networkType: Value(networkType),
        signalDbm: Value(signalDbm),
        downloadMbps: Value(downloadMbps),
        uploadMbps: Value(uploadMbps),
        latencyMs: Value(latencyMs),
        recordedAt: Value(recordedAt),
        isSynced: const Value(false),
      ),
    );
  }

  // Queue an emergency SOS alert locally
  Future<String> queueSosAlert({
    required String deviceId,
    required double lat,
    required double lon,
    required String category,
    String? message,
    bool isRelayed = false,
  }) async {
    final alertUuid = const Uuid().v4();
    await into(localSosAlerts).insert(
      LocalSosAlertsCompanion(
        alertId: Value(alertUuid),
        deviceId: Value(deviceId),
        lat: Value(lat),
        lon: Value(lon),
        category: Value(category),
        message: Value(message),
        status: const Value('queued'),
        offlineCreatedAt: Value(DateTime.now().toUtc()),
        isSynced: const Value(false),
        isRelayed: Value(isRelayed),
      ),
    );
    return alertUuid;
  }

  // Queue a check-in
  Future<int> queueCheckIn({
    required String deviceId,
    required double lat,
    required double lon,
    String status = 'safe',
  }) {
    return into(localCheckIns).insert(
      LocalCheckInsCompanion(
        deviceId: Value(deviceId),
        lat: Value(lat),
        lon: Value(lon),
        status: Value(status),
        createdAt: Value(DateTime.now().toUtc()),
        isSynced: const Value(false),
      ),
    );
  }

  // Unsynced queries
  Future<List<LocalSignalReading>> getUnsyncedReadings({int limit = 50}) {
    return (select(localSignalReadings)
          ..where((tbl) => tbl.isSynced.equals(false))
          ..limit(limit))
        .get();
  }

  Future<List<LocalSosAlert>> getUnsyncedSosAlerts({int limit = 20}) {
    return (select(localSosAlerts)
          ..where((tbl) => tbl.isSynced.equals(false))
          ..limit(limit))
        .get();
  }

  Future<List<LocalCheckIn>> getUnsyncedCheckIns({int limit = 20}) {
    return (select(localCheckIns)
          ..where((tbl) => tbl.isSynced.equals(false))
          ..limit(limit))
        .get();
  }

  // Cleanup synced rows
  Future<int> markReadingsSynced(List<int> ids) {
    return (delete(localSignalReadings)..where((tbl) => tbl.id.isIn(ids))).go();
  }

  Future<int> markSosAlertsSynced(List<int> ids) {
    return (update(localSosAlerts)..where((tbl) => tbl.id.isIn(ids))).write(
      const LocalSosAlertsCompanion(
        isSynced: Value(true),
        status: Value('sent'),
      ),
    );
  }

  Future<int> markCheckInsSynced(List<int> ids) {
    return (delete(localCheckIns)..where((tbl) => tbl.id.isIn(ids))).go();
  }
}

LazyDatabase _openConnection() {
  return LazyDatabase(() async {
    final dbFolder = await getApplicationDocumentsDirectory();
    final file = File(p.join(dbFolder.path, 'ghostnet_offline.sqlite'));
    return NativeDatabase.createInBackground(file);
  });
}
