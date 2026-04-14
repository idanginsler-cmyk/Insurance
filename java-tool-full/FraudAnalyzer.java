import java.io.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.util.*;
import java.util.stream.*;

public class FraudAnalyzer {

    // ============ מחלקות נתונים ============
    static class Claim {
        String claimId, date, insuredName, insuredId, city, employer;
        String policyType, policyStart, policyNum, coverage, provider;
        int age, amountClaimed, amountPaid;

        static Claim parse(String[] h, String[] v) {
            Map<String,String> m = new HashMap<>();
            for (int i = 0; i < h.length && i < v.length; i++) m.put(h[i].trim(), v[i].trim());
            Claim c = new Claim();
            c.claimId = m.getOrDefault("claim_id","");
            c.date = m.getOrDefault("date","");
            c.insuredName = m.getOrDefault("insured_name","");
            c.insuredId = m.getOrDefault("insured_id","");
            c.age = parseInt(m.get("age"));
            c.city = m.getOrDefault("city","");
            c.employer = m.getOrDefault("employer","");
            c.policyType = m.getOrDefault("policy_type","");
            c.policyStart = m.getOrDefault("policy_start","");
            c.policyNum = m.getOrDefault("policy_num","");
            c.coverage = m.getOrDefault("coverage","");
            c.provider = m.getOrDefault("provider","");
            c.amountClaimed = parseInt(m.get("amount_claimed"));
            c.amountPaid = parseInt(m.get("amount_paid"));
            return c;
        }
        static int parseInt(String s) {
            if (s == null || s.isEmpty()) return 0;
            try { return (int) Double.parseDouble(s.replace(",","").trim()); } catch(Exception e) { return 0; }
        }
    }

    static class Alert {
        String type, severity, title, detail;
        Alert(String t, String s, String ti, String d) { type=t; severity=s; title=ti; detail=d; }
    }

    static class RiskScore {
        String name, id;
        int claimsCount, totalAmount, providers;
        int freqScore, singleProvScore, roundScore, quickScore, familyScore, totalScore;
        String profile = "";
    }

    // ============ MAIN ============
    public static void main(String[] args) throws Exception {
        String inputFile = args.length > 0 ? args[0] : "claims.csv";
        String outputFile = args.length > 1 ? args[1] : "fraud-report.html";

        System.out.println("קורא: " + inputFile);
        List<Claim> claims = readCSV(inputFile);
        System.out.println("נטענו " + claims.size() + " תביעות");

        System.out.println("מנתח דפוסי הונאה...");
        List<Alert> alerts = new ArrayList<>();
        List<RiskScore> risks = new ArrayList<>();
        Map<String,Object> stats = analyze(claims, alerts, risks);

        System.out.println("יוצר דוח HTML...");
        String html = buildHtml(claims, alerts, risks, stats);
        Files.write(Paths.get(outputFile), html.getBytes(StandardCharsets.UTF_8));

        System.out.println("\nהסתיים!");
        System.out.println(alerts.size() + " התראות נמצאו");
        System.out.println("פתח: " + outputFile);
    }

    static List<Claim> readCSV(String path) throws IOException {
        List<Claim> list = new ArrayList<>();
        try (BufferedReader r = Files.newBufferedReader(Paths.get(path), StandardCharsets.UTF_8)) {
            String line = r.readLine();
            if (line == null) return list;
            if (line.startsWith("\uFEFF")) line = line.substring(1);
            String[] headers = splitCSV(line);
            while ((line = r.readLine()) != null) {
                if (line.trim().isEmpty()) continue;
                String[] vals = splitCSV(line);
                list.add(Claim.parse(headers, vals));
            }
        }
        return list;
    }

    static String[] splitCSV(String line) {
        List<String> out = new ArrayList<>();
        StringBuilder cur = new StringBuilder();
        boolean inQ = false;
        for (int i = 0; i < line.length(); i++) {
            char c = line.charAt(i);
            if (c == '"') inQ = !inQ;
            else if (c == ',' && !inQ) { out.add(cur.toString()); cur.setLength(0); }
            else cur.append(c);
        }
        out.add(cur.toString());
        return out.toArray(new String[0]);
    }

    static String esc(String s) {
        if (s == null) return "";
        return s.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;");
    }

    static String fmt(long n) { return String.format("%,d", n); }

    // ============ ניתוח מלא ============
    static Map<String,Object> analyze(List<Claim> claims, List<Alert> alerts, List<RiskScore> risks) {
        Map<String,Object> s = new HashMap<>();
        int total = claims.size();
        long totalClaimed = claims.stream().mapToLong(c->c.amountClaimed).sum();
        long totalPaid = claims.stream().mapToLong(c->c.amountPaid).sum();
        long uniqInsured = claims.stream().map(c->c.insuredId).distinct().count();
        long uniqProv = claims.stream().map(c->c.provider).distinct().count();
        long uniqCity = claims.stream().map(c->c.city).distinct().count();

        s.put("total", total);
        s.put("totalClaimed", totalClaimed);
        s.put("totalPaid", totalPaid);
        s.put("uniqInsured", uniqInsured);
        s.put("uniqProv", uniqProv);
        s.put("uniqCity", uniqCity);
        s.put("gap", totalClaimed - totalPaid);

        double avgClaims = (double)total / uniqInsured;

        // קיבוץ לפי מבוטח
        Map<String, List<Claim>> byPerson = claims.stream()
            .collect(Collectors.groupingBy(c -> c.insuredId));

        // 1. תדירות חריגה + חישוב ציוני סיכון
        for (Map.Entry<String,List<Claim>> e : byPerson.entrySet()) {
            List<Claim> pc = e.getValue();
            Claim f = pc.get(0);
            long sum = pc.stream().mapToLong(c->c.amountClaimed).sum();
            long provs = pc.stream().map(c->c.provider).distinct().count();

            RiskScore rs = new RiskScore();
            rs.name = f.insuredName; rs.id = f.insuredId;
            rs.claimsCount = pc.size(); rs.totalAmount = (int)sum; rs.providers = (int)provs;

            // ציון תדירות
            if (pc.size() >= avgClaims * 10) rs.freqScore = 40;
            else if (pc.size() >= avgClaims * 5) rs.freqScore = 25;
            else if (pc.size() >= avgClaims * 3) rs.freqScore = 15;

            // ציון נותן שירות בלעדי
            if (provs == 1 && pc.size() >= 3) rs.singleProvScore = 20;
            else if (provs <= 2 && pc.size() >= 5) rs.singleProvScore = 10;

            // ציון סכומים עגולים
            long roundCount = pc.stream().filter(c -> c.amountClaimed % 500 == 0 && c.amountClaimed >= 500).count();
            if (pc.size() > 0 && (double)roundCount / pc.size() > 0.5) rs.roundScore = 15;

            // ציון תביעות מיידיות
            long quickCount = pc.stream().filter(c -> daysDiff(c.policyStart, c.date) <= 60 && daysDiff(c.policyStart, c.date) >= 0).count();
            if (quickCount > 0) rs.quickScore = 15;

            rs.totalScore = rs.freqScore + rs.singleProvScore + rs.roundScore + rs.quickScore;

            // פרופיל הונאה
            if (rs.freqScore >= 40 && rs.singleProvScore >= 20) rs.profile = "🏋️ הממקסם";
            else if (rs.freqScore >= 25) rs.profile = "🏋️ ממקסם פוטנציאלי";
            else if (rs.quickScore >= 15) rs.profile = "🏃 הרוכב";
            else if (rs.singleProvScore >= 20) rs.profile = "🤝 הצמוד";
            else if (rs.roundScore >= 15) rs.profile = "✂️ המפצל";

            if (rs.totalScore > 0) risks.add(rs);

            if (pc.size() >= avgClaims * 4) {
                alerts.add(new Alert("תדירות_חריגה", "גבוה",
                    f.insuredName + " - " + pc.size() + " תביעות",
                    "ממוצע: " + (int)avgClaims + ". סה\"כ: " + fmt(sum) + " ₪, " + provs + " נותני שירות"));
            }
        }

        // 2. ריכוז נותני שירות
        Map<String,List<Claim>> byProv = claims.stream()
            .collect(Collectors.groupingBy(c -> c.provider));
        List<Map<String,Object>> provStats = new ArrayList<>();
        for (Map.Entry<String,List<Claim>> e : byProv.entrySet()) {
            double pct = (double)e.getValue().size() / total * 100;
            double avgAmt = e.getValue().stream().mapToInt(c->c.amountClaimed).average().orElse(0);
            long uniqIns = e.getValue().stream().map(c->c.insuredId).distinct().count();

            Map<String,Object> ps = new HashMap<>();
            ps.put("name", e.getKey());
            ps.put("count", e.getValue().size());
            ps.put("pct", pct);
            ps.put("avg", avgAmt);
            ps.put("insured", uniqIns);

            Map<String,Long> emps = e.getValue().stream()
                .collect(Collectors.groupingBy(c -> c.employer, Collectors.counting()));
            Map.Entry<String,Long> topEmp = emps.entrySet().stream()
                .max(Map.Entry.comparingByValue()).orElse(null);
            if (topEmp != null) {
                ps.put("topEmp", topEmp.getKey());
                ps.put("topEmpCount", topEmp.getValue());
                ps.put("topEmpPct", (double)topEmp.getValue() / e.getValue().size() * 100);
            } else {
                ps.put("topEmp", "-"); ps.put("topEmpCount", 0L); ps.put("topEmpPct", 0.0);
            }
            provStats.add(ps);

            if (pct > 5) {
                String detail = topEmp != null ?
                    "מעסיק דומיננטי: " + topEmp.getKey() + " (" + topEmp.getValue() + " תביעות, " +
                    (int)((double)topEmp.getValue() / e.getValue().size() * 100) + "%)" : "";
                alerts.add(new Alert("ריכוז_נותן_שירות", pct > 8 ? "גבוה" : "בינוני",
                    e.getKey() + " - " + e.getValue().size() + " תביעות (" + String.format("%.1f", pct) + "%)", detail));
            }
        }
        provStats.sort((a,b) -> Integer.compare((int)b.get("count"), (int)a.get("count")));
        s.put("providers", provStats);

        // 3. סכום אחיד
        for (Map.Entry<String,List<Claim>> e : byProv.entrySet()) {
            if (e.getValue().size() >= 10) {
                Map<Integer,Long> amts = e.getValue().stream()
                    .collect(Collectors.groupingBy(c->c.amountClaimed, Collectors.counting()));
                Map.Entry<Integer,Long> top = amts.entrySet().stream()
                    .max(Map.Entry.comparingByValue()).orElse(null);
                if (top != null && (double)top.getValue() / e.getValue().size() > 0.6) {
                    alerts.add(new Alert("סכום_אחיד", "בינוני",
                        e.getKey() + " - " + top.getValue() + "/" + e.getValue().size() +
                        " תביעות בסכום " + top.getKey() + " ₪",
                        String.format("%.0f%%", (double)top.getValue()/e.getValue().size()*100) + " מהתביעות באותו סכום"));
                }
            }
        }

        // 4. סכומים עגולים
        long roundCount = claims.stream().filter(c -> c.amountClaimed % 500 == 0 && c.amountClaimed >= 500).count();
        s.put("roundCount", roundCount);
        if ((double)roundCount / total > 0.03) {
            Map<String,Long> byProvRound = claims.stream()
                .filter(c -> c.amountClaimed % 500 == 0 && c.amountClaimed >= 500)
                .collect(Collectors.groupingBy(c -> c.provider, Collectors.counting()));
            String top3 = byProvRound.entrySet().stream()
                .sorted(Map.Entry.<String,Long>comparingByValue().reversed())
                .limit(3)
                .map(e -> e.getKey() + " (" + e.getValue() + ")")
                .collect(Collectors.joining(", "));
            alerts.add(new Alert("סכומים_עגולים", "בינוני",
                roundCount + " תביעות בסכומים עגולים", "נותני שירות: " + top3));
        }

        // 5. אשכולות משפחתיים
        Map<String,List<Claim>> byFamily = new HashMap<>();
        for (Claim c : claims) {
            String[] parts = c.insuredName.split(" ");
            String last = parts.length > 0 ? parts[parts.length-1] : "";
            String key = last + "|" + c.city + "|" + c.provider;
            byFamily.computeIfAbsent(key, k -> new ArrayList<>()).add(c);
        }
        List<Map<String,Object>> families = new ArrayList<>();
        for (Map.Entry<String,List<Claim>> e : byFamily.entrySet()) {
            long uniq = e.getValue().stream().map(c->c.insuredId).distinct().count();
            if (uniq >= 3 && e.getValue().size() >= 8) {
                String[] p = e.getKey().split("\\|");
                long sum = e.getValue().stream().mapToLong(c->c.amountClaimed).sum();
                Map<String,Object> f = new HashMap<>();
                f.put("lastName", p[0]); f.put("city", p[1]); f.put("provider", p[2]);
                f.put("members", uniq); f.put("claims", e.getValue().size()); f.put("total", sum);
                families.add(f);
                alerts.add(new Alert("אשכול_משפחתי", "גבוה",
                    "משפחת " + p[0] + " - " + uniq + " מבוטחים, " + e.getValue().size() + " תביעות",
                    "עיר: " + p[1] + ", נותן שירות: " + p[2] + ", סה\"כ: " + fmt(sum) + " ₪"));
            }
        }
        families.sort((a,b) -> Integer.compare(((Number)b.get("claims")).intValue(), ((Number)a.get("claims")).intValue()));
        s.put("families", families);

        // 6. התפלגות חודשית
        Map<String,long[]> monthly = new TreeMap<>();
        for (Claim c : claims) {
            if (c.date.length() >= 7) {
                String month = c.date.substring(0, 7);
                monthly.computeIfAbsent(month, k -> new long[2]);
                monthly.get(month)[0]++;
                monthly.get(month)[1] += c.amountClaimed;
            }
        }
        s.put("monthly", monthly);

        // ריצת סוף שנה
        long eoy = claims.stream().filter(c -> c.date.compareTo("2025-11-01") >= 0).count();
        long other = total - eoy;
        if (other > 0) {
            double monthlyAvg = other / 10.0;
            double eoyMonthly = eoy / 2.0;
            if (eoyMonthly > monthlyAvg * 1.3) {
                alerts.add(new Alert("ריצת_סוף_שנה", "בינוני",
                    String.format("עלייה של %.0f%% בתביעות נוב-דצמ", (eoyMonthly/monthlyAvg - 1) * 100),
                    "ממוצע חודשי: " + (int)monthlyAvg + ", נוב-דצמ: " + (int)eoyMonthly));
            }
        }

        // 7. תביעות מפוליסה חדשה
        long quick = claims.stream().filter(c -> {
            long d = daysDiff(c.policyStart, c.date);
            return d >= 0 && d <= 60;
        }).count();
        s.put("quickClaims", quick);
        if (quick > 20) {
            long quickSum = claims.stream().filter(c -> {
                long d = daysDiff(c.policyStart, c.date);
                return d >= 0 && d <= 60;
            }).mapToLong(c -> c.amountClaimed).sum();
            alerts.add(new Alert("תביעה_מיידית", "גבוה",
                quick + " תביעות תוך 60 יום מפוליסה חדשה",
                "סה\"כ: " + fmt(quickSum) + " ₪, ממוצע: " + fmt(quickSum/quick) + " ₪"));
        }

        // 8. התפלגות כיסויים
        Map<String,long[]> coverageStats = new HashMap<>();
        for (Claim c : claims) {
            coverageStats.computeIfAbsent(c.coverage, k -> new long[2]);
            coverageStats.get(c.coverage)[0]++;
            coverageStats.get(c.coverage)[1] += c.amountClaimed;
        }
        s.put("coverageStats", coverageStats);

        // 9. התפלגות ערים
        Map<String,long[]> cityStats = new HashMap<>();
        for (Claim c : claims) {
            cityStats.computeIfAbsent(c.city, k -> new long[2]);
            cityStats.get(c.city)[0]++;
            cityStats.get(c.city)[1]++;
        }
        Map<String,Long> uniqInsuredByCity = claims.stream()
            .collect(Collectors.groupingBy(c -> c.city,
                Collectors.mapping(c -> c.insuredId, Collectors.collectingAndThen(Collectors.toSet(), s1 -> (long)s1.size()))));
        s.put("cityStats", cityStats);
        s.put("cityInsured", uniqInsuredByCity);

        // 10. היסטוגרמת סכומים
        int[] hist = new int[6];
        for (Claim c : claims) {
            if (c.amountClaimed < 200) hist[0]++;
            else if (c.amountClaimed < 500) hist[1]++;
            else if (c.amountClaimed < 1000) hist[2]++;
            else if (c.amountClaimed < 2000) hist[3]++;
            else if (c.amountClaimed < 3000) hist[4]++;
            else hist[5]++;
        }
        s.put("hist", hist);

        // 11. תביעות בשבת
        long shabbat = claims.stream().filter(c -> isShabbat(c.date)).count();
        s.put("shabbat", shabbat);
        if (shabbat >= 10) {
            Map<String,Long> byProvShabbat = claims.stream().filter(c -> isShabbat(c.date))
                .collect(Collectors.groupingBy(c -> c.provider, Collectors.counting()));
            String top3 = byProvShabbat.entrySet().stream()
                .sorted(Map.Entry.<String,Long>comparingByValue().reversed())
                .limit(3).map(e -> e.getKey() + " (" + e.getValue() + ")")
                .collect(Collectors.joining(", "));
            alerts.add(new Alert("קבלות_בשבת", "בינוני",
                shabbat + " תביעות עם תאריכי טיפול בשבת",
                "נותני שירות: " + top3));
        }

        // מיון
        alerts.sort((a,b) -> {
            int aS = a.severity.equals("גבוה") ? 0 : 1;
            int bS = b.severity.equals("גבוה") ? 0 : 1;
            return Integer.compare(aS, bS);
        });
        risks.sort((a,b) -> Integer.compare(b.totalScore, a.totalScore));

        return s;
    }

    // ============ עזרים ============
    static long daysDiff(String start, String end) {
        try {
            java.time.LocalDate s = java.time.LocalDate.parse(start);
            java.time.LocalDate e = java.time.LocalDate.parse(end);
            return java.time.temporal.ChronoUnit.DAYS.between(s, e);
        } catch (Exception ex) { return -1; }
    }

    static boolean isShabbat(String date) {
        try {
            java.time.LocalDate d = java.time.LocalDate.parse(date);
            return d.getDayOfWeek() == java.time.DayOfWeek.SATURDAY;
        } catch (Exception e) { return false; }
    }

    // ============ בניית HTML עם טאבים ============
    static String buildHtml(List<Claim> claims, List<Alert> alerts, List<RiskScore> risks, Map<String,Object> s) {
        StringBuilder h = new StringBuilder();
        h.append("<!DOCTYPE html>\n<html lang=\"he\" dir=\"rtl\">\n<head>\n");
        h.append("<meta charset=\"UTF-8\">\n<title>דשבורד זיהוי הונאות</title>\n");
        appendStyles(h);
        h.append("</head>\n<body>\n");

        // NAV
        h.append("<nav>\n");
        h.append("<a href=\"#p-main\">📊 סקירה</a>\n");
        h.append("<a href=\"#p-alerts\">🚨 התראות</a>\n");
        h.append("<a href=\"#p-scoring\">🎯 דירוג</a>\n");
        h.append("<a href=\"#p-providers\">🏥 נותני שירות</a>\n");
        h.append("<a href=\"#p-geo\">📍 גיאוגרפי</a>\n");
        h.append("<a href=\"#p-coverage\">📋 כיסויים</a>\n");
        h.append("<a href=\"#p-monthly\">📅 טרנדים</a>\n");
        h.append("<a href=\"#p-financial\">💰 כספי</a>\n");
        h.append("<a href=\"#p-families\">👥 משפחות</a>\n");
        h.append("<a href=\"#p-personas\">🎭 פרופילים</a>\n");
        h.append("<a href=\"#p-watchlist\">📋 מעקב</a>\n");
        h.append("</nav>\n<div class=\"container\">\n");

        buildMainPage(h, s, alerts);
        buildAlertsPage(h, alerts);
        buildScoringPage(h, risks);
        buildProvidersPage(h, s);
        buildGeoPage(h, s);
        buildCoveragePage(h, s);
        buildMonthlyPage(h, s);
        buildFinancialPage(h, s, claims);
        buildFamiliesPage(h, s);
        buildPersonasPage(h, risks);
        buildWatchlistPage(h, risks, s);

        h.append("</div>\n</body>\n</html>\n");
        return h.toString();
    }

    static void appendStyles(StringBuilder h) {
        h.append("<style>\n");
        h.append("*{box-sizing:border-box;margin:0;padding:0}\n");
        h.append("body{font-family:system-ui,-apple-system,sans-serif;background:#f1f5f9;color:#1e293b;line-height:1.6}\n");
        h.append("nav{background:#1e293b;padding:10px 16px;position:sticky;top:0;z-index:100;overflow-x:auto;white-space:nowrap}\n");
        h.append("nav a{color:#94a3b8;text-decoration:none;padding:6px 14px;border-radius:8px;font-size:0.85em;display:inline-block;margin:2px}\n");
        h.append("nav a:hover{color:#fff;background:#334155}\n");
        h.append("h1{text-align:center;color:#1e293b;margin:16px;font-size:1.5em}\n");
        h.append("h2{color:#0f172a;margin:20px 0 10px;font-size:1.2em;border-bottom:2px solid #e2e8f0;padding-bottom:6px}\n");
        h.append("h3{color:#334155;margin:12px 0 6px;font-size:1em}\n");
        h.append(".container{max-width:1000px;margin:0 auto;padding:12px}\n");
        h.append(".card{background:#fff;border-radius:12px;padding:14px;margin:8px 0;border:1px solid #e2e8f0;box-shadow:0 1px 3px rgba(0,0,0,0.05)}\n");
        h.append(".stat-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));gap:8px;margin:10px 0}\n");
        h.append(".stat{background:#fff;border-radius:10px;padding:12px;text-align:center;border:1px solid #e2e8f0}\n");
        h.append(".stat .num{font-size:1.5em;font-weight:bold;color:#2563eb;display:block}\n");
        h.append(".stat .label{font-size:0.75em;color:#64748b}\n");
        h.append(".stat-alert .num{color:#dc2626}\n");
        h.append(".alert{border-radius:10px;padding:12px;margin:6px 0;border-right:5px solid}\n");
        h.append(".alert-high{background:#fef2f2;border-color:#dc2626}\n");
        h.append(".alert-med{background:#fffbeb;border-color:#f59e0b}\n");
        h.append(".alert h4{color:#0f172a;margin-bottom:2px;font-size:0.95em}\n");
        h.append(".alert p{font-size:0.82em;color:#64748b}\n");
        h.append(".tag{display:inline-block;padding:2px 8px;border-radius:10px;font-size:0.72em;font-weight:bold}\n");
        h.append(".tag-h{background:#dc2626;color:#fff}.tag-m{background:#f59e0b;color:#fff}.tag-l{background:#22c55e;color:#fff}\n");
        h.append("table{width:100%;border-collapse:collapse;margin:6px 0;font-size:0.82em}\n");
        h.append("th{background:#f8fafc;padding:6px 8px;text-align:right;color:#64748b;font-weight:600;border-bottom:2px solid #e2e8f0}\n");
        h.append("td{padding:6px 8px;border-bottom:1px solid #f1f5f9}\n");
        h.append("tr:hover td{background:#f8fafc}\n");
        h.append(".bar{height:18px;border-radius:4px;display:inline-block;min-width:4px}\n");
        h.append(".score-box{display:inline-block;padding:4px 10px;border-radius:6px;font-weight:bold;font-size:0.85em}\n");
        h.append(".score-high{background:#fef2f2;color:#dc2626;border:1px solid #fca5a5}\n");
        h.append(".score-med{background:#fffbeb;color:#b45309;border:1px solid #fcd34d}\n");
        h.append(".score-low{background:#f0fdf4;color:#16a34a;border:1px solid #86efac}\n");
        h.append("a.back{display:inline-block;background:#e2e8f0;color:#475569;padding:5px 12px;font-size:0.82em;border-radius:6px;text-decoration:none;margin:4px}\n");
        h.append("a.back:hover{background:#cbd5e1}\n");
        h.append(".page{display:none}.page:target{display:block}\n");
        h.append("#p-main{display:block}#p-main:target~#p-main{display:block}:target~#p-main{display:none}\n");
        h.append("</style>\n");
    }

    static void buildMainPage(StringBuilder h, Map<String,Object> s, List<Alert> alerts) {
        h.append("<div class=\"page\" id=\"p-main\">\n");
        h.append("<h1>🔍 דשבורד זיהוי הונאות - ביטוח בריאות</h1>\n");
        h.append("<div class=\"card\" style=\"text-align:center;background:#eff6ff;border-color:#bfdbfe\">\n");
        h.append("<p style=\"color:#1e40af\">").append(fmt((int)s.get("total")))
         .append(" תביעות | ").append(s.get("uniqInsured")).append(" מבוטחים | ")
         .append(s.get("uniqProv")).append(" נותני שירות | ")
         .append(alerts.size()).append(" התראות</p></div>\n");

        long high = alerts.stream().filter(a->a.severity.equals("גבוה")).count();
        long med = alerts.size() - high;

        h.append("<div class=\"stat-grid\">\n");
        h.append("<div class=\"stat\"><span class=\"num\">").append(fmt((int)s.get("total"))).append("</span><span class=\"label\">תביעות</span></div>\n");
        h.append("<div class=\"stat\"><span class=\"num\">").append(fmt((long)s.get("totalClaimed"))).append("₪</span><span class=\"label\">נתבע</span></div>\n");
        h.append("<div class=\"stat\"><span class=\"num\">").append(fmt((long)s.get("totalPaid"))).append("₪</span><span class=\"label\">שולם</span></div>\n");
        h.append("<div class=\"stat\"><span class=\"num\">").append(s.get("uniqInsured")).append("</span><span class=\"label\">מבוטחים</span></div>\n");
        h.append("<div class=\"stat stat-alert\"><span class=\"num\">").append(high).append("</span><span class=\"label\">🔴 גבוהות</span></div>\n");
        h.append("<div class=\"stat\"><span class=\"num\" style=\"color:#f59e0b\">").append(med).append("</span><span class=\"label\">🟡 בינוניות</span></div>\n");
        h.append("</div>\n");

        h.append("<h2>🔴 התראות חמורות</h2>\n");
        int c = 0;
        for (Alert a : alerts) {
            if (a.severity.equals("גבוה") && c++ < 5) {
                h.append("<div class=\"alert alert-high\">\n<h4><span class=\"tag tag-h\">").append(a.type).append("</span> ").append(esc(a.title)).append("</h4>\n<p>").append(esc(a.detail)).append("</p>\n</div>\n");
            }
        }
        h.append("</div>\n");
    }

    static void buildAlertsPage(StringBuilder h, List<Alert> alerts) {
        h.append("<div class=\"page\" id=\"p-alerts\">\n");
        h.append("<a href=\"#p-main\" class=\"back\">← סקירה</a>\n");
        h.append("<h1>🚨 כל ההתראות (").append(alerts.size()).append(")</h1>\n");
        for (Alert a : alerts) {
            String cls = a.severity.equals("גבוה") ? "alert-high" : "alert-med";
            String tagCls = a.severity.equals("גבוה") ? "tag-h" : "tag-m";
            String icon = a.severity.equals("גבוה") ? "🔴" : "🟡";
            h.append("<div class=\"alert ").append(cls).append("\">\n")
             .append("<h4><span class=\"tag ").append(tagCls).append("\">").append(icon).append(" ").append(a.type).append("</span> ").append(esc(a.title)).append("</h4>\n")
             .append("<p>").append(esc(a.detail)).append("</p>\n</div>\n");
        }
        h.append("</div>\n");
    }

    static void buildScoringPage(StringBuilder h, List<RiskScore> risks) {
        h.append("<div class=\"page\" id=\"p-scoring\">\n");
        h.append("<a href=\"#p-main\" class=\"back\">← סקירה</a>\n");
        h.append("<h1>🎯 דירוג סיכון - מבוטחים</h1>\n");
        h.append("<table>\n<tr><th>#</th><th>מבוטח</th><th>ת.ז.</th><th>תביעות</th><th>סכום</th><th>נ.ש.</th><th>פרופיל</th><th>ציון</th></tr>\n");
        int i = 1;
        for (RiskScore r : risks) {
            if (i > 30) break;
            String scoreCls = r.totalScore >= 50 ? "score-high" : r.totalScore >= 25 ? "score-med" : "score-low";
            h.append("<tr><td>").append(i++).append("</td><td>").append(esc(r.name))
             .append("</td><td>").append(esc(r.id)).append("</td><td>").append(r.claimsCount)
             .append("</td><td>").append(fmt(r.totalAmount)).append("₪</td><td>").append(r.providers)
             .append("</td><td>").append(r.profile).append("</td><td><span class=\"score-box ").append(scoreCls).append("\">").append(r.totalScore).append("</span></td></tr>\n");
        }
        h.append("</table>\n</div>\n");
    }

    static void buildProvidersPage(StringBuilder h, Map<String,Object> s) {
        h.append("<div class=\"page\" id=\"p-providers\">\n");
        h.append("<a href=\"#p-main\" class=\"back\">← סקירה</a>\n");
        h.append("<h1>🏥 ניתוח נותני שירות</h1>\n");
        List<Map<String,Object>> provs = (List<Map<String,Object>>)s.get("providers");
        h.append("<table>\n<tr><th>נותן שירות</th><th>תביעות</th><th>%</th><th>מעסיק דומיננטי</th><th>סכום ממוצע</th><th>סיכון</th></tr>\n");
        for (Map<String,Object> p : provs) {
            double pct = (double)p.get("pct");
            double empPct = (double)p.get("topEmpPct");
            String risk = (pct > 8 || empPct > 40) ? "🔴" : (pct > 5) ? "🟡" : "🟢";
            String rowStyle = (pct > 8) ? " style=\"background:#fef2f2\"" : (pct > 5) ? " style=\"background:#fffbeb\"" : "";
            h.append("<tr").append(rowStyle).append("><td>").append(esc((String)p.get("name")))
             .append("</td><td>").append(p.get("count"))
             .append("</td><td>").append(String.format("%.1f%%", pct))
             .append("</td><td>").append(esc((String)p.get("topEmp"))).append(" (").append(String.format("%.0f%%", empPct)).append(")")
             .append("</td><td>").append(String.format("%.0f₪", (double)p.get("avg")))
             .append("</td><td>").append(risk).append("</td></tr>\n");
        }
        h.append("</table>\n</div>\n");
    }

    static void buildGeoPage(StringBuilder h, Map<String,Object> s) {
        h.append("<div class=\"page\" id=\"p-geo\">\n");
        h.append("<a href=\"#p-main\" class=\"back\">← סקירה</a>\n");
        h.append("<h1>📍 ניתוח גיאוגרפי</h1>\n");
        Map<String,long[]> cityStats = (Map<String,long[]>)s.get("cityStats");
        Map<String,Long> cityInsured = (Map<String,Long>)s.get("cityInsured");
        List<Map.Entry<String,long[]>> sorted = cityStats.entrySet().stream()
            .sorted((a,b) -> Long.compare(b.getValue()[0], a.getValue()[0]))
            .collect(Collectors.toList());
        long max = sorted.isEmpty() ? 1 : sorted.get(0).getValue()[0];

        h.append("<table>\n<tr><th>עיר</th><th>תביעות</th><th>מבוטחים</th><th>תביעות/מבוטח</th><th></th></tr>\n");
        double avgRatio = cityStats.values().stream().mapToLong(v -> v[0]).sum() / (double)cityInsured.values().stream().mapToLong(v->v).sum();
        for (Map.Entry<String,long[]> e : sorted) {
            long claims = e.getValue()[0];
            long insured = cityInsured.getOrDefault(e.getKey(), 1L);
            double ratio = insured > 0 ? (double)claims / insured : 0;
            int w = (int)((double)claims / max * 200);
            String rowStyle = ratio > avgRatio * 1.5 ? " style=\"background:#fef2f2\"" : "";
            String color = ratio > avgRatio * 1.5 ? "#dc2626" : "#2563eb";
            h.append("<tr").append(rowStyle).append("><td>").append(esc(e.getKey()))
             .append("</td><td>").append(claims).append("</td><td>").append(insured)
             .append("</td><td>").append(String.format("%.1f", ratio))
             .append("</td><td><div class=\"bar\" style=\"width:").append(w).append("px;background:").append(color).append("\"></div></td></tr>\n");
        }
        h.append("</table>\n</div>\n");
    }

    static void buildCoveragePage(StringBuilder h, Map<String,Object> s) {
        h.append("<div class=\"page\" id=\"p-coverage\">\n");
        h.append("<a href=\"#p-main\" class=\"back\">← סקירה</a>\n");
        h.append("<h1>📋 ניתוח כיסויים</h1>\n");
        Map<String,long[]> cov = (Map<String,long[]>)s.get("coverageStats");
        h.append("<table>\n<tr><th>כיסוי</th><th>תביעות</th><th>סה\"כ סכום</th><th>ממוצע</th><th></th></tr>\n");
        long max = cov.values().stream().mapToLong(v -> v[0]).max().orElse(1);
        cov.entrySet().stream()
            .sorted((a,b) -> Long.compare(b.getValue()[0], a.getValue()[0]))
            .forEach(e -> {
                long c = e.getValue()[0];
                long total = e.getValue()[1];
                int w = (int)((double)c / max * 200);
                h.append("<tr><td>").append(esc(e.getKey())).append("</td><td>").append(c)
                 .append("</td><td>").append(fmt(total)).append("₪</td><td>").append(fmt(total/Math.max(c,1))).append("₪")
                 .append("</td><td><div class=\"bar\" style=\"width:").append(w).append("px;background:#3b82f6\"></div></td></tr>\n");
            });
        h.append("</table>\n</div>\n");
    }

    static void buildMonthlyPage(StringBuilder h, Map<String,Object> s) {
        h.append("<div class=\"page\" id=\"p-monthly\">\n");
        h.append("<a href=\"#p-main\" class=\"back\">← סקירה</a>\n");
        h.append("<h1>📅 טרנדים חודשיים</h1>\n");
        Map<String,long[]> monthly = (Map<String,long[]>)s.get("monthly");
        long max = monthly.values().stream().mapToLong(v -> v[0]).max().orElse(1);
        double avg = monthly.values().stream().mapToLong(v -> v[0]).average().orElse(0);

        h.append("<table>\n<tr><th>חודש</th><th>תביעות</th><th>סכום</th><th></th><th>הערה</th></tr>\n");
        for (Map.Entry<String,long[]> e : monthly.entrySet()) {
            long c = e.getValue()[0];
            long total = e.getValue()[1];
            int w = (int)((double)c / max * 250);
            String color = c > avg * 1.3 ? "#dc2626" : c > avg * 1.1 ? "#f59e0b" : "#2563eb";
            String note = c > avg * 1.3 ? "<span class=\"tag tag-h\">🔴 חריג</span>" : "";
            String rowStyle = c > avg * 1.3 ? " style=\"background:#fef2f2\"" : "";
            h.append("<tr").append(rowStyle).append("><td>").append(e.getKey())
             .append("</td><td>").append(c).append("</td><td>").append(fmt(total)).append("₪")
             .append("</td><td><div class=\"bar\" style=\"width:").append(w).append("px;background:").append(color).append("\"></div></td><td>").append(note).append("</td></tr>\n");
        }
        h.append("</table>\n");
        h.append("<div class=\"card\"><p>ממוצע חודשי: ").append(String.format("%.0f", avg)).append(" תביעות</p></div>\n");
        h.append("</div>\n");
    }

    static void buildFinancialPage(StringBuilder h, Map<String,Object> s, List<Claim> claims) {
        h.append("<div class=\"page\" id=\"p-financial\">\n");
        h.append("<a href=\"#p-main\" class=\"back\">← סקירה</a>\n");
        h.append("<h1>💰 ניתוח כספי</h1>\n");

        long claimed = (long)s.get("totalClaimed");
        long paid = (long)s.get("totalPaid");
        long gap = (long)s.get("gap");
        int total = (int)s.get("total");

        h.append("<div class=\"stat-grid\">\n");
        h.append("<div class=\"stat\"><span class=\"num\">").append(fmt(claimed)).append("₪</span><span class=\"label\">נתבע</span></div>\n");
        h.append("<div class=\"stat\"><span class=\"num\">").append(fmt(paid)).append("₪</span><span class=\"label\">שולם</span></div>\n");
        h.append("<div class=\"stat stat-alert\"><span class=\"num\">").append(fmt(gap)).append("₪</span><span class=\"label\">פער (").append(gap*100/Math.max(claimed,1)).append("%)</span></div>\n");
        h.append("<div class=\"stat\"><span class=\"num\">").append(fmt(claimed/total)).append("₪</span><span class=\"label\">ממוצע לתביעה</span></div>\n");
        h.append("</div>\n");

        // Top 10 מבוטחים יקרים
        h.append("<h2>Top 10 מבוטחים יקרים</h2>\n");
        Map<String, long[]> byIns = new HashMap<>();
        Map<String, String> names = new HashMap<>();
        for (Claim c : claims) {
            byIns.computeIfAbsent(c.insuredId, k -> new long[3]);
            byIns.get(c.insuredId)[0]++;
            byIns.get(c.insuredId)[1] += c.amountClaimed;
            byIns.get(c.insuredId)[2] += c.amountPaid;
            names.put(c.insuredId, c.insuredName);
        }
        List<Map.Entry<String,long[]>> topIns = byIns.entrySet().stream()
            .sorted((a,b) -> Long.compare(b.getValue()[2], a.getValue()[2]))
            .limit(10).collect(Collectors.toList());
        h.append("<table>\n<tr><th>#</th><th>מבוטח</th><th>תביעות</th><th>שולם</th><th>ממוצע</th></tr>\n");
        int i = 1;
        for (Map.Entry<String,long[]> e : topIns) {
            h.append("<tr><td>").append(i++).append("</td><td>").append(esc(names.get(e.getKey())))
             .append("</td><td>").append(e.getValue()[0]).append("</td><td>").append(fmt(e.getValue()[2])).append("₪")
             .append("</td><td>").append(fmt(e.getValue()[2]/Math.max(e.getValue()[0],1))).append("₪</td></tr>\n");
        }
        h.append("</table>\n");

        // היסטוגרמת סכומים
        h.append("<h2>התפלגות סכומים</h2>\n");
        int[] hist = (int[])s.get("hist");
        String[] labels = {"0-200", "200-500", "500-1K", "1K-2K", "2K-3K", "3K+"};
        String[] colors = {"#22c55e","#22c55e","#2563eb","#2563eb","#f59e0b","#dc2626"};
        h.append("<table>\n<tr><th>טווח</th><th>תביעות</th><th>%</th><th></th></tr>\n");
        for (int j = 0; j < hist.length; j++) {
            int w = hist[j]/2;
            double pct = (double)hist[j]/total*100;
            h.append("<tr><td>").append(labels[j]).append("₪</td><td>").append(hist[j])
             .append("</td><td>").append(String.format("%.1f%%", pct))
             .append("</td><td><div class=\"bar\" style=\"width:").append(w).append("px;background:").append(colors[j]).append("\"></div></td></tr>\n");
        }
        h.append("</table>\n</div>\n");
    }

    static void buildFamiliesPage(StringBuilder h, Map<String,Object> s) {
        h.append("<div class=\"page\" id=\"p-families\">\n");
        h.append("<a href=\"#p-main\" class=\"back\">← סקירה</a>\n");
        h.append("<h1>👥 אשכולות משפחתיים</h1>\n");
        List<Map<String,Object>> families = (List<Map<String,Object>>)s.get("families");
        if (families.isEmpty()) {
            h.append("<div class=\"card\"><p>לא נמצאו אשכולות משפחתיים חשודים</p></div>\n");
        } else {
            h.append("<table>\n<tr><th>משפחה</th><th>עיר</th><th>נותן שירות</th><th>מבוטחים</th><th>תביעות</th><th>סה\"כ</th></tr>\n");
            for (Map<String,Object> f : families) {
                h.append("<tr style=\"background:#fef2f2\"><td><b>").append(esc((String)f.get("lastName")))
                 .append("</b></td><td>").append(esc((String)f.get("city")))
                 .append("</td><td>").append(esc((String)f.get("provider")))
                 .append("</td><td>").append(f.get("members"))
                 .append("</td><td>").append(f.get("claims"))
                 .append("</td><td>").append(fmt((long)f.get("total"))).append("₪</td></tr>\n");
            }
            h.append("</table>\n");
        }
        h.append("</div>\n");
    }

    static void buildPersonasPage(StringBuilder h, List<RiskScore> risks) {
        h.append("<div class=\"page\" id=\"p-personas\">\n");
        h.append("<a href=\"#p-main\" class=\"back\">← סקירה</a>\n");
        h.append("<h1>🎭 פרופילי הונאה</h1>\n");
        Map<String,List<RiskScore>> byProfile = new LinkedHashMap<>();
        for (RiskScore r : risks) {
            if (!r.profile.isEmpty()) {
                byProfile.computeIfAbsent(r.profile, k -> new ArrayList<>()).add(r);
            }
        }
        for (Map.Entry<String,List<RiskScore>> e : byProfile.entrySet()) {
            h.append("<div class=\"card\" style=\"border-right:5px solid #dc2626\">\n");
            h.append("<h2 style=\"border:none;margin:0;color:#dc2626\">").append(e.getKey()).append(" (").append(e.getValue().size()).append(")</h2>\n");
            h.append("<table>\n<tr><th>מבוטח</th><th>תביעות</th><th>סכום</th><th>ציון</th></tr>\n");
            int c = 0;
            for (RiskScore r : e.getValue()) {
                if (c++ >= 5) break;
                String scoreCls = r.totalScore >= 50 ? "score-high" : "score-med";
                h.append("<tr><td>").append(esc(r.name)).append("</td><td>").append(r.claimsCount)
                 .append("</td><td>").append(fmt(r.totalAmount)).append("₪")
                 .append("</td><td><span class=\"score-box ").append(scoreCls).append("\">").append(r.totalScore).append("</span></td></tr>\n");
            }
            h.append("</table>\n</div>\n");
        }
        h.append("</div>\n");
    }

    static void buildWatchlistPage(StringBuilder h, List<RiskScore> risks, Map<String,Object> s) {
        h.append("<div class=\"page\" id=\"p-watchlist\">\n");
        h.append("<a href=\"#p-main\" class=\"back\">← סקירה</a>\n");
        h.append("<h1>📋 Watchlist - רשימת מעקב</h1>\n");

        long high = risks.stream().filter(r -> r.totalScore >= 50).count();
        long med = risks.stream().filter(r -> r.totalScore >= 25 && r.totalScore < 50).count();

        h.append("<div class=\"stat-grid\">\n");
        h.append("<div class=\"stat stat-alert\"><span class=\"num\">").append(high).append("</span><span class=\"label\">🔴 סיכון גבוה</span></div>\n");
        h.append("<div class=\"stat\"><span class=\"num\" style=\"color:#f59e0b\">").append(med).append("</span><span class=\"label\">🟡 בינוני</span></div>\n");
        h.append("</div>\n");

        h.append("<h2>🔴 מבוטחים במעקב (ציון 50+)</h2>\n");
        h.append("<table>\n<tr><th>#</th><th>מבוטח</th><th>ת.ז.</th><th>פרופיל</th><th>תביעות</th><th>ציון</th></tr>\n");
        int i = 1;
        for (RiskScore r : risks) {
            if (r.totalScore < 50) continue;
            if (i > 20) break;
            h.append("<tr style=\"background:#fef2f2\"><td>").append(i++).append("</td><td>").append(esc(r.name))
             .append("</td><td>").append(esc(r.id)).append("</td><td>").append(r.profile)
             .append("</td><td>").append(r.claimsCount).append("</td><td><span class=\"score-box score-high\">").append(r.totalScore).append("</span></td></tr>\n");
        }
        h.append("</table>\n");

        h.append("<h2>פעולות מומלצות</h2>\n<div class=\"card\">\n");
        h.append("<p>1. ⚡ <b>דחוף:</b> בירור עם ").append(high).append(" מבוטחים בסיכון גבוה</p>\n");
        h.append("<p>2. 📞 <b>בינוני:</b> דגימה אקראית של ").append(med).append(" מבוטחים בסיכון בינוני</p>\n");
        h.append("<p>3. 📋 <b>שוטף:</b> הוספת סף בקרה לפוליסות חדשות (60 יום ראשונים)</p>\n");
        h.append("</div>\n</div>\n");
    }
}
