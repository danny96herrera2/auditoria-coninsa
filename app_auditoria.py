with col_bot2:
            # BOTÓN DE IMPRESIÓN MEJORADO PARA STREAMLIT CLOUD
            components.html(
                """
                <script>
                function printPage() {
                    try {
                        // Intenta imprimir la ventana principal de Streamlit
                        window.parent.print();
                    } catch (e) {
                        try {
                            // Si está bloqueado, intenta imprimir la pestaña completa
                            window.top.print();
                        } catch (e2) {
                            // Último recurso
                            window.print();
                        }
                    }
                }
                </script>
                <button onclick="printPage()" style="
                    background-color:#002856;
                    color:white;
                    padding:10px 20px;
                    border:none;
                    border-radius:5px;
                    cursor:pointer;
                    font-weight:bold;
                    font-family:sans-serif;
                    width: 100%;
                ">🖨️ Imprimir Reporte (o presiona Ctrl+P)</button>
                """,
                height=55
            )
