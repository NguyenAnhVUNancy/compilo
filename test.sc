int main(int X,int Y) {
    /*
    if(X){
        printf(X/Y); //ok
    }
    else{
        printf(Y);
    }*/
    for(int Z=(X+2); Z>(Y-2); Z--){
        printf((Z>X)||(Z<Y));
    }
    /*
    printf(Y);
    */
    return(0);
}
