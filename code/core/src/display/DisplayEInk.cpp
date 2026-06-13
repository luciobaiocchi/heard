#include "DisplayEInk.h"
#include "Constants.h"


// Costruttore con inizializzazione dei membri
DisplayEInk::DisplayEInk()
    : epd2(EINK_CS, EINK_DC, EINK_RST, EINK_BUSY),
      display(epd2),
      x(0), y(0), alt(0)
{}


void DisplayEInk::begin() {
    display.init();   // inizializza il display (e non epd2)
    display.setRotation(2);
    display.setTextColor(GxEPD_BLACK);
    display.setFullWindow();
    display.firstPage();
    do {
        display.fillScreen(GxEPD_WHITE);
    } while (display.nextPage());
    Serial.println("display");
}


void DisplayEInk::drawCenteredText(const char* text, int y, int textSize) {
    display.setTextSize(textSize);
    int16_t x1, y1;
    uint16_t w, h;
    display.getTextBounds(text, 0, 0, &x1, &y1, &w, &h);
    int16_t x = (display.width() - w) / 2;
    display.setCursor(x, y);
    display.print(text);
}


void DisplayEInk::drawLoadingScreen() {
    Serial.println("Display");
    display.setFullWindow();
    //delay(100);
    display.setPartialWindow(0, 0, display.width(), display.height());

    display.firstPage();
    do {
        display.fillScreen(GxEPD_WHITE);
        drawCenteredText("HEARD", 120, 3);
    } while (display.nextPage());
}


void DisplayEInk::drawMainScreen() {
    updateHeader(true, false);
    updateBody("Connect to  receive \n   data", 2);
    updateFooter("HOME");
}

void DisplayEInk::drawReceivedPOints(int points, double distanceMeters) {
    updateHeader(true, false);

    // Componiamo il messaggio su due righe: "Received X points" e "Path length: Y m"
    String msg = "Received: " + String(points) + " points\n" +
                 "Length: " + String(distanceMeters) + " m";

    updateBody(msg.c_str(), 1);

    updateFooter("HOME");
}


void DisplayEInk::updateHeader(bool loraState, bool gpsState) {
    display.setPartialWindow(0, 0, display.width(), 30);
    display.firstPage();
    do {
        display.fillRect(0, 0, display.width(), 30, GxEPD_WHITE);
        display.drawRect(0, 0, display.width(), 30, GxEPD_BLACK);
        //display.setCursor(15, 10);
        //display.setTextSize(2);
        //display.print("G:v  L:x");


        char lora = loraState ? 'v' : 'f';
        char gps = gpsState ? 'v' : 'f';
        String text = "G:";
        text+=gps;
        text+= "  L:";
        text+= lora;

        drawCenteredText(text.c_str(), 10, 2);

    } while (display.nextPage());
}


void DisplayEInk::updateFooter(const char* text) {
    int footerH = 20;
    int yStart = display.height() - footerH;
    display.setPartialWindow(0, yStart, display.width(), footerH);
    display.firstPage();
    do {
        display.fillRect(0, yStart, display.width(), footerH, GxEPD_WHITE);
        display.drawRect(0, yStart, display.width(), footerH, GxEPD_BLACK);
        //display.setCursor(30, display.height() - 17);
        //display.setTextSize(1);
        drawCenteredText(text, display.height() - 13, 1);

        //display.print("Footer text");
    } while (display.nextPage());
}


void DisplayEInk::updateBody(const char* text, int textSize) {
    int headerH = 30;
    int footerH = 20;
    int bodyH = display.height() - headerH - footerH;
    display.setPartialWindow(0, headerH, display.width(), bodyH);
    display.firstPage();
    do {
        display.fillRect(0, headerH, display.width(), bodyH, GxEPD_WHITE);

        // Calcolo altezza testo per centrare verticalmente (approssimato)
        int textHeight = textSize * 8;  // 8 pixel per dimensione base (modifica se serve)
        int yPos = headerH + (bodyH / 2) - (textHeight / 2);

        drawCenteredText(text, yPos - 30, textSize);
    } while (display.nextPage());
}

// Navigazione e accessori
void DisplayEInk::navigateTo(double x_, double y_) {
    x = x_;
    y = y_;
    
    drawMainScreen();
}

void DisplayEInk::clearScreen() {
    display.setFullWindow();
    display.firstPage();
    do {
        display.fillScreen(GxEPD_WHITE);
    } while (display.nextPage());
}

int DisplayEInk::getAlt() {
    return alt;
}



void DisplayEInk::loadActivityScreen() {
    // Disegna tutto lo schermo (tranne header se già presente)
    display.setPartialWindow(0, headerH, display.width(), display.height() - headerH);
    display.firstPage();
    do {
        // Area utente
        display.fillRect(0, headerH, display.width(), userH, GxEPD_WHITE);
        drawCenteredText("P: --", headerH + 10, 2);
        drawCenteredText("S: --", headerH + 35, 2);

        // Tabella membri
        int tableY = headerH + userH;
        display.fillRect(0, tableY, display.width(), rowH * tableRows, GxEPD_WHITE);

        // Intestazione tabella
        display.setCursor(5, tableY + 15);
        display.print("NAME");
        display.setCursor(display.width() / 2, tableY + 15);
        display.print("STATE");

            // Righe vuote iniziali
        for (int i = 0; i < tableRows; i++) {
            char nome[20];
            char stato[20];
            snprintf(nome, sizeof(nome), "Pers%d", i);
            snprintf(stato, sizeof(stato), "  I%d", i);
            drawTableRow(i, nome, stato, false);
        }

    } while (display.nextPage());
}

void DisplayEInk::updateUserData(const char* posizione, const char* stato) {
    display.setPartialWindow(0, headerH, display.width(), userH);
    display.firstPage();
    do {
        display.fillRect(0, headerH, display.width(), userH, GxEPD_WHITE);
        drawCenteredText((String("") + posizione).c_str(), headerH + 10, 2);
        drawCenteredText((String("S: ") + stato).c_str(), headerH + 45, 2);
    } while (display.nextPage());
}

void DisplayEInk::updateTableRow(int rowIndex, const char* nome, const char* stato) {
    int tableY = headerH + userH + rowIndex * rowH;
    display.setPartialWindow(0, tableY, display.width(), rowH);
    display.firstPage();
    do {
        display.fillRect(0, tableY, display.width(), rowH, GxEPD_WHITE);
        display.setCursor(5, tableY + 15);
        display.print(nome);
        display.setCursor(display.width() / 2, tableY + 15);
        display.print(stato);
    } while (display.nextPage());
}

void DisplayEInk::drawTableRow(int rowIndex, const char* nome, const char* stato, bool isHeader) {
    int tableY = headerH + userH + rowIndex * rowH;
    if (!isHeader){
        tableY+= 30;
    }
    display.setCursor(5, tableY + 15);
    display.print(nome);
    display.setCursor(display.width() / 2, tableY + 15);
    display.print(stato);
}




