import java.io.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.util.*;
import java.util.stream.*;

public class FraudAnalyzer {

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
        Alert(String t, String s, String ti, String d) {
            type=t; severity=s; title=ti; detail=d;
        }
    }

    public static void main(String[] args) throws Exception {
        String inputFile = args.length > 0 ? args[0] : "claims.csv";
        String outputFile = args.length > 1 ? args[1] : "fraud-report.html";

        System.out.println("📂 קורא: " + inputFile);
        List<Claim> claims = readCSV(inputFile);
        System.out.println("✓ נטענו " + claims.size() + " תביעות");

        System.out.println("🔍 מנתח דפוסי הונאה...");
        List<Alert> alerts = new ArrayList<>();
        Map<String,Object> stats = analyze(claims, alerts);

        System.out.println("📝 יוצר דוח HTML...");
        String html = buildHtml(claims, alerts, stats);
        Files.write(Paths.get(outputFile), html.getBytes(StandardCharsets.UTF_8));

        System.out.println("\n✅ הסתיים!");
        System.out.println("📊 " + alerts.size() + " התראות נמצאו");
        System.out.println("🌐 פתח: " + outputFile);
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

    static Map<String,Object> analyze(List<Claim> claims, List<Alert> alerts) {
        Map<String,Object> s = new HashMap<>();
        int total = claims.size();
        long totalClaimed = claims.stream().mapToLong(c->c.amountClaimed).sum();
        long totalPaid = claims.stream().mapToLong(c->c.amountPaid).sum();
        long uniqInsured = claims.stream().map(c->c.insuredId).distinct().count();
        long uniqProv = claims.stream().map(c->c.provider).distinct().count();

        s.put("total", total);
        s.put("totalClaimed", totalClaimed);
        s.put("totalPaid", totalPaid);
        s.put("uniqInsured", uniqInsured);
        s.put("uniqProv", uniqProv);

        // 1. High frequency
        double avgClaims = (double)total / uniqInsured;
        Map<String, List<Claim>> byPerson = claims.stream()
            .collect(Collectors.groupingBy(c -> c.insuredId));
        for (Map.Entry<String,List<Claim>> e : byPerson.entrySet()) {
            if (e.getValue().size() >= avgClaims * 4) {
                Claim f = e.getValue().get(0);
                long sum = e.getValue().stream().mapToLong(c->c.amountClaimed).sum();
                alerts.add(new Alert("תדירות_חריגה", "גבוה",
                    f.insuredName + " - " + e.getValue().size() + " תביעות",
                    "ממוצע: " + (int)avgClaims + ". מבוטח: " + e.getValue().size() +
                    ". סה\"כ: " + String.format("%,d", sum) + " ₪"));
            }
        }

        // 2. Provider concentration
        Map<String,List<Claim>> byProv = claims.stream()
            .collect(Collectors.groupingBy(c -> c.provider));
        for (Map.Entry<String,List<Claim>> e : byProv.entrySet()) {
            double pct = (double)e.getValue().size() / total * 100;
            if (pct > 5) {
                Map<String,Long> emps = e.getValue().stream()
                    .collect(Collectors.groupingBy(c -> c.employer, Collectors.counting()));
                Map.Entry<String,Long> topEmp = emps.entrySet().stream()
                    .max(Map.Entry.comparingByValue()).orElse(null);
                String detail = "";
                if (topEmp != null) {
                    double empPct = (double)topEmp.getValue() / e.getValue().size() * 100;
                    detail = "מעסיק דומיננטי: " + topEmp.getKey() +
                        " (" + topEmp.getValue() + " תביעות, " + (int)empPct + "%)";
                }
                alerts.add(new Alert("ריכוז_נותן_שירות",
                    pct > 8 ? "גבוה" : "בינוני",
                    e.getKey() + " - " + e.getValue().size() + " תביעות (" +
                    String.format("%.1f", pct) + "%)", detail));
            }
        }

        // 3. Uniform amounts
        for (Map.Entry<String,List<Claim>> e : byProv.entrySet()) {
            if (e.getValue().size() >= 10) {
                Map<Integer,Long> amts = e.getValue().stream()
                    .collect(Collectors.groupingBy(c->c.amountClaimed, Collectors.counting()));
                Map.Entry<Integer,Long> top = amts.entrySet().stream()
                    .max(Map.Entry.comparingByValue()).orElse(null);
                if (top != null) {
                    double pct = (double)top.getValue() / e.getValue().size();
                    if (pct > 0.6) {
                        alerts.add(new Alert("סכום_אחיד", "בינוני",
                            e.getKey() + " - " + top.getValue() + "/" + e.getValue().size() +
                            " תביעות בסכום " + top.getKey() + " ₪",
                            String.format("%.0f%%", pct*100) + " מהתביעות באותו סכום בדיוק"));
                    }
                }
            }
        }

        // 4. Round amounts
        long roundCount = claims.stream().filter(c -> c.amountClaimed % 500 == 0 && c.amountClaimed >= 500).count();
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
                roundCount + " תביעות בסכומים עגולים",
                "נותני שירות: " + top3));
        }

        // 5. Family clusters
        Map<String,List<Claim>> byFamily = new HashMap<>();
        for (Claim c : claims) {
            String[] parts = c.insuredName.split(" ");
            String last = parts.length > 0 ? parts[parts.length-1] : "";
            String key = last + "|" + c.city + "|" + c.provider;
            byFamily.computeIfAbsent(key, k -> new ArrayList<>()).add(c);
        }
        for (Map.Entry<String,List<Claim>> e : byFamily.entrySet()) {
            long uniq = e.getValue().stream().map(c->c.insuredId).distinct().count();
            if (uniq >= 3 && e.getValue().size() >= 8) {
                String[] p = e.getKey().split("\\|");
                alerts.add(new Alert("אשכול_משפחתי", "גבוה",
                    "משפחת " + p[0] + " - " + uniq + " מבוטחים, " +
                    e.getValue().size() + " תביעות",
                    "עיר: " + p[1] + ", נותן שירות: " + p[2]));
            }
        }

        // Sort by severity
        alerts.sort((a,b) -> {
            int aS = a.severity.equals("גבוה") ? 0 : 1;
            int bS = b.severity.equals("גבוה") ? 0 : 1;
            return Integer.compare(aS, bS);
        });

        return s;
    }

    static String buildHtml(List<Claim> claims, List<Alert> alerts, Map<String,Object> s) {
        StringBuilder h = new StringBuilder();
        h.append("<!DOCTYPE html>\n<html lang=\"he\" dir=\"rtl\">\n<head>\n");
        h.append("<meta charset=\"UTF-8\">\n<title>דוח זיהוי הונאות</title>\n<style>\n");
        h.append("*{box-sizing:border-box;margin:0;padding:0}\n");
        h.append("body{font-family:system-ui,sans-serif;background:#f1f5f9;color:#1e293b;padding:16px;line-height:1.6;max-width:1000px;margin:0 auto}\n");
        h.append("h1{text-align:center;color:#dc2626;margin:16px 0;font-size:1.6em}\n");
        h.append("h2{color:#0f172a;margin:24px 0 10px;font-size:1.2em;border-bottom:2px solid #e2e8f0;padding-bottom:6px}\n");
        h.append(".card{background:#fff;border-radius:12px;padding:14px;margin:8px 0;border:1px solid #e2e8f0;box-shadow:0 1px 3px rgba(0,0,0,0.05)}\n");
        h.append(".stat-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px;margin:12px 0}\n");
        h.append(".stat{background:#fff;border-radius:10px;padding:14px;text-align:center;border:1px solid #e2e8f0}\n");
        h.append(".stat .num{font-size:1.6em;font-weight:bold;color:#2563eb;display:block}\n");
        h.append(".stat .label{font-size:0.8em;color:#64748b}\n");
        h.append(".alert{border-radius:10px;padding:14px;margin:8px 0;border-right:5px solid}\n");
        h.append(".alert-high{background:#fef2f2;border-color:#dc2626}\n");
        h.append(".alert-med{background:#fffbeb;border-color:#f59e0b}\n");
        h.append(".alert h4{color:#0f172a;margin-bottom:4px}\n");
        h.append(".alert p{font-size:0.85em;color:#64748b}\n");
        h.append(".tag{display:inline-block;padding:2px 10px;border-radius:12px;font-size:0.75em;font-weight:bold}\n");
        h.append(".tag-h{background:#dc2626;color:#fff}.tag-m{background:#f59e0b;color:#fff}\n");
        h.append("table{width:100%;border-collapse:collapse;margin:10px 0;font-size:0.85em;background:#fff}\n");
        h.append("th{background:#f8fafc;padding:8px;text-align:right;color:#64748b;border-bottom:2px solid #e2e8f0}\n");
        h.append("td{padding:8px;border-bottom:1px solid #f1f5f9}\n");
        h.append("</style>\n</head>\n<body>\n");

        h.append("<h1>🔍 דוח זיהוי הונאות - ביטוח בריאות</h1>\n");
        h.append("<div class=\"card\" style=\"text-align:center\"><p>נותח אוטומטית | ")
         .append(s.get("total")).append(" תביעות | ")
         .append(alerts.size()).append(" התראות</p></div>\n");

        h.append("<h2>📊 סטטיסטיקות</h2>\n<div class=\"stat-grid\">\n");
        h.append("<div class=\"stat\"><span class=\"num\">").append(String.format("%,d", s.get("total"))).append("</span><span class=\"label\">תביעות</span></div>\n");
        h.append("<div class=\"stat\"><span class=\"num\">").append(String.format("%,d₪", s.get("totalClaimed"))).append("</span><span class=\"label\">נתבע</span></div>\n");
        h.append("<div class=\"stat\"><span class=\"num\">").append(String.format("%,d₪", s.get("totalPaid"))).append("</span><span class=\"label\">שולם</span></div>\n");
        h.append("<div class=\"stat\"><span class=\"num\">").append(s.get("uniqInsured")).append("</span><span class=\"label\">מבוטחים</span></div>\n");
        h.append("<div class=\"stat\"><span class=\"num\">").append(s.get("uniqProv")).append("</span><span class=\"label\">נותני שירות</span></div>\n");
        long high = alerts.stream().filter(a->a.severity.equals("גבוה")).count();
        h.append("<div class=\"stat\" style=\"border-color:#dc2626\"><span class=\"num\" style=\"color:#dc2626\">").append(high).append("</span><span class=\"label\">🔴 גבוהות</span></div>\n");
        h.append("</div>\n");

        h.append("<h2>🚨 התראות</h2>\n");
        for (Alert a : alerts) {
            String cls = a.severity.equals("גבוה") ? "alert-high" : "alert-med";
            String tagCls = a.severity.equals("גבוה") ? "tag-h" : "tag-m";
            String icon = a.severity.equals("גבוה") ? "🔴" : "🟡";
            h.append("<div class=\"alert ").append(cls).append("\">\n");
            h.append("<h4><span class=\"tag ").append(tagCls).append("\">").append(icon).append(" ").append(a.type).append("</span> ").append(esc(a.title)).append("</h4>\n");
            h.append("<p>").append(esc(a.detail)).append("</p>\n");
            h.append("</div>\n");
        }

        h.append("</body></html>");
        return h.toString();
    }

    static String esc(String s) {
        if (s == null) return "";
        return s.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;");
    }
}
