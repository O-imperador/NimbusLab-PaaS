import {ThemeProvider } from './useTheme';
import DeployApp from './comp/deployApp.jsx';

const App = () => {
    return(
    <ThemeProvider>
        <DeployApp />
    </ThemeProvider>
    )
}

export default App;