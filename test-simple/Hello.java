import java.io.*;
import java.awt.Desktop;

public class Hello {
    public static void main(String[] args) throws Exception {
        System.out.println("שלום! הקוד רץ בהצלחה!");

        String html = "<!DOCTYPE html>\n" +
            "<html lang='he' dir='rtl'>\n" +
            "<head><meta charset='UTF-8'><title>בדיקה</title></head>\n" +
            "<body style='font-family:sans-serif;text-align:center;padding:50px;background:#0f172a;color:#fff'>\n" +
            "<h1 style='color:#22c55e'>✅ הקוד עבד!</h1>\n" +
            "<p>זה דף שנוצר על ידי Java במחשב שלך.</p>\n" +
            "<p style='color:#94a3b8'>אם אתה רואה את זה - הכל עובד!</p>\n" +
            "</body></html>";

        File file = new File("hello.html");
        FileWriter writer = new FileWriter(file);
        writer.write(html);
        writer.close();

        System.out.println("נוצר קובץ: hello.html");
        System.out.println("פותח בדפדפן...");

        try {
            Desktop.getDesktop().browse(file.toURI());
        } catch (Exception e) {
            System.out.println("לא הצלחתי לפתוח אוטומטית - פתח ידנית את hello.html");
        }
    }
}
